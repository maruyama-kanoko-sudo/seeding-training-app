// ============================================================
// 新人研修シート AI管理 — Google Apps Script v3
// ============================================================
// 構成前提：
//   ・1タブ = 1名分の研修シート（タブ名 = 名前）
//   ・A列の特定行（下記 STATUS_ROWS）にステータスを入力
//     値: 未着手 / 進行中 / 完了 / 停止中
//   ・A列の特定行（下記 TEST_ROWS）にテスト合否を入力
//     値: 未実施 / 合格 / 不合格
//
// 使い方：
//   1. Apps Script にこのコードを貼り付けて保存
//   2. 「研修管理 > 初期セットアップ実行」を実行
//   3. 「研修管理 > 自動実行トリガー設定」を実行
//   4. 各自の研修シートタブに入力 → ダッシュボードを確認
// ============================================================

// ---- 定数 ----
var STATUS_ROWS   = [3, 52, 73, 85, 100, 124, 134, 151, 170, 184, 196, 210, 224, 235, 242]; // 15日分ステータス行
var DATE_ROWS     = [2, 51, 72, 84,  99, 123, 133, 150, 169, 183, 195, 209, 223, 234, 241]; // 各日の日付行（STATUS_ROWS - 1）
var TEST_ROWS     = [103, 173]; // テスト合否行（A103, A173）
var TOTAL_DAYS    = 15;
var SYSTEM_SHEETS = ["ダッシュボード"]; // スキャン対象外のシート名

// ============================================================
// 起動時メニュー
// ============================================================
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("研修管理")
    .addItem("🔄 進捗スキャン＆ダッシュボード更新", "scanAndUpdate")
    .addSeparator()
    .addItem("⚙️ 初期セットアップ実行", "setupSheets")
    .addItem("⏰ 自動実行トリガー設定", "setupTriggers")
    .addToUi();
}

// ============================================================
// onEdit：A2（1日目の日付）変更 → 残14日分を自動入力
// ============================================================
function onEdit(e) {
  var sheet = e.range.getSheet();
  if (SYSTEM_SHEETS.indexOf(sheet.getName()) !== -1) return;
  if (e.range.getRow() === 2 && e.range.getColumn() === 1) {
    autoFillDates_(sheet, e.range.getValue());
  }
}

function autoFillDates_(sheet, startDate) {
  if (!startDate || !(startDate instanceof Date)) return;
  for (var i = 1; i < DATE_ROWS.length; i++) {
    var d = new Date(startDate.getTime());
    d.setDate(d.getDate() + i);
    sheet.getRange(DATE_ROWS[i], 1).setValue(d).setNumberFormat("yyyy/MM/dd");
  }
}

// ============================================================
// メイン：全タブをスキャン → ダッシュボード更新
// ============================================================
function scanAndUpdate() {
  updateDashboard();
  SpreadsheetApp.getActiveSpreadsheet().toast("スキャン＆ダッシュボード更新完了！", "研修管理", 3);
}

// ============================================================
// ステータス読み込み（A列の STATUS_ROWS 各行）
// ============================================================
function readStatuses_(sheet) {
  var statuses = [];
  for (var i = 0; i < STATUS_ROWS.length; i++) {
    var val = String(sheet.getRange(STATUS_ROWS[i], 1).getValue()).trim();
    if (val === "" || val === "null" || val === "undefined") val = "未着手";
    statuses.push(val);
  }
  return statuses; // 長さ15の配列（1日目〜15日目に対応）
}

// ============================================================
// テスト状況読み込み（A103, A173）
// ============================================================
function readTestStatus_(sheet) {
  var results = [];
  for (var i = 0; i < TEST_ROWS.length; i++) {
    var val = String(sheet.getRange(TEST_ROWS[i], 1).getValue()).trim();
    if (val === "" || val === "null" || val === "undefined") val = "未実施";
    results.push(val);
  }

  // 優先順位: 不合格 > 合格（全て合格） > 未実施
  if (results.indexOf("不合格") !== -1) return "再テスト";
  if (results.every(function(v) { return v === "合格"; })) return "合格"; // 全て「合格」の時のみ
  return "未実施"; // 想定外の値も未実施扱い
}

// ============================================================
// 進捗集計
// ============================================================
function calcProgress_(statuses) {
  var completedCount = 0;
  var currentDay     = 0; // 完了 or 進行中 の最大日番号
  var incompleteDays = []; // 完了以外の日番号

  for (var i = 0; i < statuses.length; i++) {
    var dayNum = i + 1;
    var s = statuses[i];

    if (s === "完了") {
      completedCount++;
      if (dayNum > currentDay) currentDay = dayNum;
    } else {
      incompleteDays.push(dayNum);
      if (s === "進行中" && dayNum > currentDay) currentDay = dayNum;
    }
  }

  var rate = Math.round(completedCount / TOTAL_DAYS * 100); // %

  return {
    completedCount: completedCount,
    rate:           rate,
    currentDay:     currentDay,      // 0 = まだ進んでいない
    incompleteDays: incompleteDays   // 完了以外の日番号リスト
  };
}

// ============================================================
// B列チェックボックスの完了率を計算
// ============================================================
function calcCheckboxRate_(sheet) {
  var data    = sheet.getDataRange().getValues();
  var total   = 0;
  var checked = 0;
  for (var i = 0; i < data.length; i++) {
    var bVal = data[i][1]; // B列（index 1）
    if (typeof bVal === 'boolean') {
      total++;
      if (bVal === true) checked++;
    }
  }
  return total > 0 ? Math.round(checked / total * 100) : 0;
}

// ============================================================
// ステータス判定（優先順位あり）
// ============================================================
function determineStatus_(statuses) {
  if (statuses.indexOf("停止中") !== -1) return "停止中";
  if (statuses.indexOf("進行中") !== -1) return "進行中";
  var allComplete = statuses.every(function(s) { return s === "完了"; });
  if (allComplete) return "完了";
  return "未着手";
}

// ============================================================
// 要対応判定
// ============================================================
function determineAction_(status, testStatus, statuses, progress) {
  var alerts = [];

  // アラート条件
  if (progress.rate < 50 && progress.currentDay >= 8) alerts.push("🟡注意");
  var notStartedCount = statuses.filter(function(s) { return s === "未着手"; }).length;
  if (notStartedCount >= 2) alerts.push("🟡注意");
  // 重複除去
  alerts = alerts.filter(function(v, i, a) { return a.indexOf(v) === i; });

  var alertStr = alerts.length > 0 ? alerts.join("") + " " : "";

  // 要対応アクション（優先順位あり）
  if (testStatus === "再テスト") return alertStr + "再テスト対応";
  if (status === "停止中")     return alertStr + "即1on1";

  // 進行中が2日以上連続しているか
  var progressingCount = 0;
  var maxConsecutiveProgressing = 0;
  for (var i = 0; i < statuses.length; i++) {
    if (statuses[i] === "進行中") {
      progressingCount++;
      if (progressingCount > maxConsecutiveProgressing) maxConsecutiveProgressing = progressingCount;
    } else {
      progressingCount = 0;
    }
  }
  if (maxConsecutiveProgressing >= 2) return alertStr + "進捗確認";

  if (notStartedCount >= 2) return alertStr + "着手催促";
  if (status === "完了")     return "対応不要";

  return alertStr.trim() || "経過観察";
}

// ============================================================
// ダッシュボード更新
// ============================================================
function updateDashboard() {
  var ss        = SpreadsheetApp.getActiveSpreadsheet();
  var dashSheet = ss.getSheetByName("ダッシュボード");
  if (!dashSheet) {
    dashSheet = ss.insertSheet("ダッシュボード");
  }

  // 全研修タブを収集
  var sheets    = ss.getSheets();
  var members   = [];

  for (var i = 0; i < sheets.length; i++) {
    var sheet = sheets[i];
    var name  = sheet.getName();
    if (SYSTEM_SHEETS.indexOf(name) !== -1) continue;

    var statuses      = readStatuses_(sheet);
    var testStatus    = readTestStatus_(sheet);
    var progress      = calcProgress_(statuses);
    var checkboxRate  = calcCheckboxRate_(sheet);          // ★ チェック数率
    var status        = determineStatus_(statuses);        // 内部判定用（表示しない）
    var action        = determineAction_(status, testStatus, statuses, { rate: checkboxRate, currentDay: progress.currentDay });

    // 現在日：A2の開始日から今日が何日目か
    var currentDayStr = "日付未入力";
    var startDateVal  = sheet.getRange(2, 1).getValue(); // A2 = 研修開始日
    if (startDateVal instanceof Date && !isNaN(startDateVal)) {
      var startDate = new Date(startDateVal);
      startDate.setHours(0, 0, 0, 0);
      var todayDate = new Date();
      todayDate.setHours(0, 0, 0, 0);
      var dayNum = Math.floor((todayDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
      if (dayNum < 1) dayNum = 1; // 開始日前でも1日目扱い
      currentDayStr = dayNum + "日目";
    }

    var rateStr           = checkboxRate + "%";            // ★ チェック数率を使用
    var incompleteDaysStr = progress.incompleteDays.length > 0
      ? progress.incompleteDays.map(function(d) { return d + "日"; }).join(", ")
      : "なし";

    members.push({
      name:           name,
      currentDay:     currentDayStr,
      rate:           rateStr,
      rateNum:        checkboxRate,
      incompleteDays: incompleteDaysStr,
      testStatus:     testStatus,
      action:         action
    });
  }

  // ソート: 要対応（停止中/不合格）→ 注意あり → 進行中 → 未着手 → 完了
  members.sort(function(a, b) {
    // 🟡注意 が付いているものを上に
    var aAlert = a.action.indexOf("🟡") !== -1 ? 0 : 1;
    var bAlert = b.action.indexOf("🟡") !== -1 ? 0 : 1;
    if (aAlert !== bAlert) return aAlert - bAlert;
    return a.rateNum - b.rateNum; // 進捗率が低い順
  });

  // ---- 書き込み ----
  dashSheet.clearContents();
  dashSheet.clearFormats();

  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy/MM/dd HH:mm");
  var writeRow = 1;

  // タイトル
  dashSheet.getRange(writeRow, 1).setValue("📊 研修進捗ダッシュボード（更新：" + today + "）");
  dashSheet.getRange(writeRow, 1).setFontWeight("bold").setFontSize(13);
  writeRow += 2;

  // サマリー
  var alertCount    = members.filter(function(m) { return m.action.indexOf("🟡") !== -1; }).length;
  var completeCount = members.filter(function(m) { return m.rateNum === 100; }).length;

  dashSheet.getRange(writeRow, 1, 1, 6).setValues([[
    "🟡 要注意", alertCount + "人",
    "🟢 完了（100%）", completeCount + "人",
    "合計", members.length + "人"
  ]]);
  dashSheet.getRange(writeRow, 1, 1, 6).setFontWeight("bold");
  writeRow += 2;

  if (members.length === 0) {
    dashSheet.getRange(writeRow, 1).setValue("研修シートのタブが見つかりませんでした。");
    return;
  }

  // ヘッダー（ステータス列を削除）
  var headers = ["名前", "現在日", "進捗率", "未完了日", "テスト状況", "要対応"];
  dashSheet.getRange(writeRow, 1, 1, headers.length).setValues([headers]);
  dashSheet.getRange(writeRow, 1, 1, headers.length)
    .setBackground("#34495e")
    .setFontColor("#ffffff")
    .setFontWeight("bold")
    .setHorizontalAlignment("center");
  writeRow++;

  // データ行
  for (var j = 0; j < members.length; j++) {
    var m = members[j];
    var rowData = [m.name, m.currentDay, m.rate, m.incompleteDays, m.testStatus, m.action];
    dashSheet.getRange(writeRow, 1, 1, headers.length).setValues([rowData]);

    // 行の背景色
    var bg = "#ffffff";
    if (m.action.indexOf("即1on1") !== -1)   bg = "#fde8e8"; // 停止中
    else if (m.action.indexOf("🟡") !== -1)  bg = "#fff9e6"; // 注意あり
    else if (m.rateNum === 100)              bg = "#e8f8ee"; // 完了
    else if (m.rateNum === 0)               bg = "#f5f5f5"; // 未着手
    else                                    bg = "#e8f4fd"; // 進行中
    dashSheet.getRange(writeRow, 1, 1, headers.length).setBackground(bg);

    writeRow++;
  }

  // 列幅
  dashSheet.setColumnWidth(1, 130); // 名前
  dashSheet.setColumnWidth(2, 150); // 現在日
  dashSheet.setColumnWidth(3, 70);  // 進捗率
  dashSheet.setColumnWidth(4, 220); // 未完了日
  dashSheet.setColumnWidth(5, 90);  // テスト状況
  dashSheet.setColumnWidth(6, 200); // 要対応
}

// ============================================================
// 初期セットアップ（ダッシュボードシートを作成）
// ============================================================
function setupSheets() {
  var ss        = SpreadsheetApp.getActiveSpreadsheet();
  var dashSheet = ss.getSheetByName("ダッシュボード");
  if (!dashSheet) {
    dashSheet = ss.insertSheet("ダッシュボード");
  }

  SpreadsheetApp.getUi().alert(
    "セットアップ完了！\n\n" +
    "次のステップ：\n" +
    "① 各新人の研修シートタブを作成\n" +
    "   （タブ名 = 表示名。例：田中花子）\n\n" +
    "② A列の以下の行にステータスを入力：\n" +
    "   行 3, 52, 73, 85, 100, 124, 134, 151,\n" +
    "       170, 184, 196, 210, 224, 235, 242\n" +
    "   値: 未着手 / 進行中 / 完了 / 停止中\n\n" +
    "③ A103, A173 にテスト合否を入力：\n" +
    "   値: 未実施 / 合格 / 不合格\n\n" +
    "④ 「研修管理 > 進捗スキャン＆ダッシュボード更新」を実行\n\n" +
    "⑤ 「研修管理 > 自動実行トリガー設定」を実行"
  );
}

// ============================================================
// 時間トリガー設定（毎朝8時に自動スキャン）
// ============================================================
function setupTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "scanAndUpdate") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger("scanAndUpdate")
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .create();

  SpreadsheetApp.getUi().alert(
    "自動実行トリガーを設定しました！\n\n" +
    "毎朝8時に全タブをスキャンして\n" +
    "ダッシュボードが自動更新されます。"
  );
}
