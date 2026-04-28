/**
 * HTC WF 新人研修シート - キングダムデザイン適用スクリプト
 *
 * 使い方:
 *   1. Google Spreadsheet を開く
 *   2. 「拡張機能」>「Apps Script」を開く
 *   3. このファイルの中身を全てコピーして貼り付け、保存（Ctrl+S）
 *   4. 関数 applyKingdomDesign を選択して「実行」ボタンをクリック
 *   5. 権限承認のダイアログが出たら「許可」を選択
 *
 * ※ 実行前にスプレッドシートのバックアップを取ることをおすすめします！
 * ※ デザインを元に戻したい場合は resetDesign() を実行してください。
 */

// ============================================================
//  設定定数
// ============================================================

const NUM_BANNER_ROWS = 3;  // 昇格バナーの行数
const NUM_TITLE_ROWS  = 4;  // タイトルバナーの行数

const LEVEL_CONFIG = {
  shinpei:  { minDay: 1,  maxDay: 5,  header: '#3B5998', bg: '#E8EEF7', fg: '#FFFFFF', darkBg: '#1A237E' },
  hyakunin: { minDay: 6,  maxDay: 9,  header: '#2E7D32', bg: '#E8F5E9', fg: '#FFFFFF', darkBg: '#1B5E20' },
  sennin:   { minDay: 10, maxDay: 14, header: '#E65100', bg: '#FFF3E0', fg: '#FFFFFF', darkBg: '#BF360C' },
  shogun:   { minDay: 15, maxDay: 99, header: '#880E4F', bg: '#FDE8E8', fg: '#FFD700', darkBg: '#880E4F' },
};

const LEVEL_BANNERS = {
  1:  {
    lines: [
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
      '🪖　【 新兵 】として任命される！　天下への道、今ここから始まる！　🪖',
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
    ],
    darkBg: '#1A237E',
  },
  6:  {
    lines: [
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
      '🎉　昇格！【 百人将 】に就任！百の命を背負い、さらなる高みへ！　🎉',
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
    ],
    darkBg: '#1B5E20',
  },
  10: {
    lines: [
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
      '🔥　昇格！【 千人将 】に就任！千の命を率いてさらなる高みへ！　🔥',
      '⚔️  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚔️',
    ],
    darkBg: '#BF360C',
  },
  15: {
    lines: [
      '👑  ═══════════════════════════════════════════════════════════════════════════  👑',
      '✨　昇格！【 将軍 】に就任！天下統一への最後の門が開かれた！　✨',
      '👑  ═══════════════════════════════════════════════════════════════════════════  👑',
    ],
    darkBg: '#880E4F',
  },
};

// ============================================================
//  メニュー追加（スプレッドシートを開いたとき自動で呼ばれる）
// ============================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('⚔️ 研修管理')
    .addItem('✨ キングダムデザインを適用', 'applyKingdomDesign')
    .addSeparator()
    .addItem('↩️ デザインをリセット', 'resetDesign')
    .addToUi();
}

// ============================================================
//  メイン関数
// ============================================================

function applyKingdomDesign() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getActiveSheet();

  // ---- Step 1: 日目ヘッダー行を検索 ----
  let dayHeaders = findDayHeaders_(sheet);
  if (dayHeaders.length === 0) {
    SpreadsheetApp.getUi().alert('エラー: 「X日目」のヘッダー行が見つかりませんでした。\nデザインを適用したいシートがアクティブになっているか確認してください。');
    return;
  }

  // ---- Step 2: 昇格バナーを挿入（下から順に処理して行番号ズレを防ぐ） ----
  const levelStartDays = new Set([1, 6, 10, 15]);
  const bannersToInsert = dayHeaders
    .filter(d => levelStartDays.has(d.day))
    .sort((a, b) => b.row - a.row); // 下から処理

  const numCols = Math.max(sheet.getLastColumn(), 7);

  for (const { row, day } of bannersToInsert) {
    const banner = LEVEL_BANNERS[day];
    sheet.insertRowsBefore(row, NUM_BANNER_ROWS);

    for (let i = 0; i < NUM_BANNER_ROWS; i++) {
      const r     = sheet.getRange(row + i, 1, 1, numCols);
      const isMid = (i === 1);
      r.merge();
      r.setValue(banner.lines[i]);
      r.setBackground(banner.darkBg);
      r.setFontColor(isMid ? '#FFD700' : '#546E7A');
      r.setFontWeight('bold');
      r.setFontSize(isMid ? 14 : 9);
      r.setHorizontalAlignment('center');
      r.setVerticalAlignment('middle');
      r.setFontFamily('Arial');
      sheet.setRowHeight(row + i, isMid ? 40 : 16);
    }
  }

  SpreadsheetApp.flush();

  // ---- Step 3: 再スキャンして日目ヘッダーと各行に色を適用 ----
  dayHeaders = findDayHeaders_(sheet);
  const lastRow  = sheet.getLastRow();
  const lastCol  = sheet.getLastColumn();
  const allData  = sheet.getRange(1, 1, lastRow, Math.min(lastCol, 8)).getValues();

  for (let idx = 0; idx < dayHeaders.length; idx++) {
    const { row, day } = dayHeaders[idx];
    const level   = getLevelConfig_(day);
    const nextRow = idx + 1 < dayHeaders.length ? dayHeaders[idx + 1].row : lastRow + 1;

    // 日目ヘッダー行のスタイル
    const hRange = sheet.getRange(row, 1, 1, lastCol);
    hRange.setBackground(level.header);
    hRange.setFontColor(level.fg);
    hRange.setFontWeight('bold');
    hRange.setFontSize(12);
    hRange.setVerticalAlignment('middle');
    sheet.setRowHeight(row, 32);

    // コンテンツ行のスタイル
    let toggle = 0;
    for (let r = row + 1; r < nextRow; r++) {
      const rowRange   = sheet.getRange(r, 1, 1, lastCol);
      const primaryText = getPrimaryText_(allData[r - 1]);

      if (primaryText.includes('営業トレーニング')) {
        rowRange.setBackground('#FFF9C4');
        rowRange.setFontWeight('bold');
        rowRange.setFontSize(11);
        sheet.setRowHeight(r, 26);
      } else if (primaryText.includes('手続きリスト')) {
        rowRange.setBackground('#FCE4EC');
        rowRange.setFontWeight('bold');
        rowRange.setFontSize(11);
        sheet.setRowHeight(r, 26);
      } else if (primaryText.includes('リクエスト項目')) {
        rowRange.setBackground('#E8EAF6');
        rowRange.setFontWeight('bold');
        rowRange.setFontSize(11);
        sheet.setRowHeight(r, 26);
      } else {
        toggle++;
        rowRange.setBackground(toggle % 2 === 0 ? '#FFFFFF' : level.bg);
      }
    }
  }

  // ---- Step 4: 最上部にタイトルバナーを追加 ----
  sheet.insertRowsBefore(1, NUM_TITLE_ROWS);
  const finalCols = sheet.getLastColumn();

  // タイトル行
  const title1 = sheet.getRange(1, 1, 1, finalCols);
  title1.merge();
  title1.setValue('⚔️　HTC WF 新人研修シート　〜 キングダムへの道 〜　⚔️');
  title1.setBackground('#0D1B2A');
  title1.setFontColor('#FFD700');
  title1.setFontWeight('bold');
  title1.setFontSize(18);
  title1.setHorizontalAlignment('center');
  title1.setVerticalAlignment('middle');
  sheet.setRowHeight(1, 55);

  // レベル進行ライン
  const title2 = sheet.getRange(2, 1, 1, finalCols);
  title2.merge();
  title2.setValue('🪖 新兵（1日目〜）　→　⚔️ 百人将（6日目〜）　→　🔥 千人将（10日目〜）　→　👑 将軍（15日目〜）');
  title2.setBackground('#1C2B3A');
  title2.setFontColor('#B0BEC5');
  title2.setFontWeight('bold');
  title2.setFontSize(12);
  title2.setHorizontalAlignment('center');
  title2.setVerticalAlignment('middle');
  sheet.setRowHeight(2, 34);

  // 応援メッセージ
  const title3 = sheet.getRange(3, 1, 1, finalCols);
  title3.merge();
  title3.setValue('💪　研修を完走して将軍を目指せ！ふんばれ新人！　💪');
  title3.setBackground('#263238');
  title3.setFontColor('#80CBC4');
  title3.setFontWeight('bold');
  title3.setFontSize(11);
  title3.setHorizontalAlignment('center');
  title3.setVerticalAlignment('middle');
  sheet.setRowHeight(3, 28);

  // スペーサー
  const spacer = sheet.getRange(4, 1, 1, finalCols);
  spacer.merge();
  spacer.setBackground('#0D1B2A');
  sheet.setRowHeight(4, 6);

  // ---- Step 5: 列幅の調整 ----
  sheet.setColumnWidth(1, 110);  // A列: 日付・ステータス
  sheet.setColumnWidth(2, 240);  // B列: セクション見出し
  if (finalCols >= 5) {
    sheet.setColumnWidth(5, 350); // E列: タスク内容
  }

  SpreadsheetApp.flush();

  SpreadsheetApp.getUi().alert(
    '🎉 キングダムデザインの適用が完了しました！\n\n' +
    '　🪖 新兵    → 1〜5日目\n' +
    '　⚔️ 百人将  → 6〜9日目\n' +
    '　🔥 千人将  → 10〜14日目\n' +
    '　👑 将軍    → 15日目〜\n\n' +
    '天下統一を目指して研修を頑張ってください！'
  );
}

// ============================================================
//  リセット関数（デザインを元に戻したい場合）
// ============================================================

function resetDesign() {
  const ui = SpreadsheetApp.getUi();
  const res = ui.alert(
    '⚠️ 確認',
    '全セルの書式（色・フォント・結合）をリセットします。\nバナー行は手動で削除してください。よろしいですか？',
    ui.ButtonSet.YES_NO
  );
  if (res !== ui.Button.YES) return;

  const sheet = SpreadsheetApp.getActiveSheet();
  const range = sheet.getDataRange();
  range.setBackground(null);
  range.setFontColor(null);
  range.setFontWeight('normal');
  range.setFontSize(10);
  range.breakApart(); // セル結合を解除

  ui.alert('書式をリセットしました。\nバナー行（デザイン用に挿入された行）は手動で削除してください。');
}

// ============================================================
//  ユーティリティ関数
// ============================================================

function findDayHeaders_(sheet) {
  const lastRow  = sheet.getLastRow();
  const lastCol  = Math.min(sheet.getLastColumn(), 8);
  const data     = sheet.getRange(1, 1, lastRow, lastCol).getValues();
  const results  = [];

  for (let i = 0; i < data.length; i++) {
    for (let j = 0; j < data[i].length; j++) {
      const match = String(data[i][j] || '').match(/^(\d+)日目/);
      if (match) {
        results.push({ row: i + 1, day: parseInt(match[1]) });
        break;
      }
    }
  }
  return results;
}

function getLevelConfig_(day) {
  if (day >= 15) return LEVEL_CONFIG.shogun;
  if (day >= 10) return LEVEL_CONFIG.sennin;
  if (day >= 6)  return LEVEL_CONFIG.hyakunin;
  return LEVEL_CONFIG.shinpei;
}

function getPrimaryText_(rowData) {
  for (const cell of rowData) {
    const t = String(cell || '').trim();
    if (t.length > 0) return t;
  }
  return '';
}
