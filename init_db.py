"""Initialize database with seed data."""
from database import Base, engine, SessionLocal
import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def init():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.Team).count() > 0:
        print("データベースは既に初期化されています。")
        db.close()
        return

    # Teams
    team_a = models.Team(name="Aチーム")
    team_b = models.Team(name="Bチーム")
    db.add_all([team_a, team_b])
    db.flush()

    # Users
    admin = models.User(name="管理者", email="admin@example.com", password_hash=pwd_context.hash("admin123"), role="admin", team_id=team_a.id)
    user1 = models.User(name="田中 太郎", email="tanaka@example.com", password_hash=pwd_context.hash("test123"), role="user", team_id=team_a.id)
    user2 = models.User(name="鈴木 花子", email="suzuki@example.com", password_hash=pwd_context.hash("test123"), role="user", team_id=team_b.id)
    db.add_all([admin, user1, user2])
    db.flush()

    # ========== Categories (モード別) ==========
    cat_fill = models.Category(
        name="穴埋めシーディング",
        description="トーク台本の空欄を埋めてシーディングトークのパターンを身につけよう！まずはお手本に近づける練習から。"
    )
    cat_free = models.Category(
        name="記述式シーディング",
        description="自分の言葉でシーディングトークを自由に組み立てる記述式トレーニング。表現力を鍛えよう。"
    )
    cat_voice = models.Category(
        name="音声入力シーディング",
        description="実際に声に出してシーディングトークを練習しよう！マイクを使ってリアルな営業トークを体感。"
    )
    db.add_all([cat_fill, cat_free, cat_voice])
    db.flush()

    # ========== 穴埋めシーディング Questions ==========
    db.add_all([
        models.Question(
            category_id=cat_fill.id,
            customer_text="受講料が高くて、正直払えるか不安です。もう少し安ければよかったんですけど...",
            expected_points="共感→はるかさんトーク→今始めることのメリット提示→一緒に考えようクロージング",
            difficulty="normal",
            fill_template="""[＿＿＿＿]の気持ち、全然その気持ち持ったままで大丈夫ですよ。

実は前にはるかさんっていう医療事務で働かれてた方がいて、手取りが[＿＿＿＿]くらいで、そこから家賃とか生活費払ったらほとんど残らない状態だったんですよね。

その方も同じように悩まれてたんですけど、「今の状況で[＿＿＿＿]ってたら、いつになるか分からない」って言ってたんです。

もし1ヶ月で[＿＿＿＿]可能性があるなら、今始めるのか1年後始めるのかで[＿＿＿＿]くらい差が出るかもって考えたら、今やるしかないって思ったらしくて。

〇〇さんも、今の状況の中でどうやったら進められそうか、[＿＿＿＿]？""",
        ),
        models.Question(
            category_id=cat_fill.id,
            customer_text="今月は出費が多くて、来月だったらもう少し余裕があるんですけど、それまで待てますか？",
            expected_points="共感→先延ばしのリスク言語化→第三者トーク→今できる方法を一緒に考えるクロージング",
            difficulty="normal",
            fill_template="""[＿＿＿＿]の気持ち、すごく分かります。

ただ一つだけ確認させてください。来月になったら、今月と状況は[＿＿＿＿]変わりそうですか？

実は「来月にしよう」って言ってた方が、気づいたら[＿＿＿＿]たったって方もいて。

待っている間にも[＿＿＿＿]という状況は続いてしまうんですよね。

〇〇さんの場合、今の状況でできることを一緒に[＿＿＿＿]ませんか？""",
        ),
        models.Question(
            category_id=cat_fill.id,
            customer_text="夫に相談してから決めたいと思います。一人では決められなくて...",
            expected_points="共感→やりたい気持ち確認→山北さんトーク→報告スタイル提案",
            difficulty="normal",
            fill_template="""[＿＿＿＿]って思うの、すごく大事なことだと思いますし、心配になる気持ちもすごく分かります。

ちなみに、もし反対された場合って、気持ち[＿＿＿＿]そうですか？

前に山北さんっていう方がいて、旦那さんに最初すごく反対されてたんですけど、「[＿＿＿＿]」って言って自分で決断されたんですよね。

結果が出てから旦那さんに[＿＿＿＿]てもらえて、"あの時やってよかった"って言ってましたね。

〇〇さんとしては、やりたい気持ちとやりたくない気持ち、[＿＿＿＿]？""",
        ),
        models.Question(
            category_id=cat_fill.id,
            customer_text="他のスクールとも比べてみたいと思っています。もう少し調べてから決めます",
            expected_points="比較を肯定→信頼不足として扱う→まこさんトーク→引っかかっている点の深掘り",
            difficulty="normal",
            fill_template="""[＿＿＿＿]っていう気持ち、全然自然だと思います。

前にまこさんっていう元看護師の方も、いろんなスクール見てた方だったんですよね。

その方が言ってたのが「[＿＿＿＿]って後悔するくらいなら、[＿＿＿＿]」って。

最初に案件取れた時に、めちゃくちゃ嬉しくて[＿＿＿＿]したら、そこから応援してもらえるようになったって言ってました。

比較すること自体は全然いいと思うんですけど、〇〇さんとしては、今一番[＿＿＿＿]ポイントってどこですか？""",
        ),
        models.Question(
            category_id=cat_fill.id,
            customer_text="仕事が忙しくて、時間が取れるか不安です。毎日残業続きで...",
            expected_points="共感→いくみさんトーク→時間は作るもの→スケジュール一緒に確認クロージング",
            difficulty="normal",
            fill_template="""時間の不安、[＿＿＿＿]分かります。

実は前にいくみさんっていう、イベント会社で照明のお仕事されてる方がいて、[＿＿＿＿]という状況だったんですよ。

その時いくみさんが言ってたのが「じゃあ時間できるのを待ちますって言っても、[＿＿＿＿]」って。

だったら、今ある状況の中でできる方法を[＿＿＿＿]しかないって言って始められたんですよね。

1日のスケジュールを[＿＿＿＿]単位で全部洗い出したら、意外と[＿＿＿＿]時間が出てきたって言ってました。

〇〇さんも、今の生活の中でどこなら少しでも[＿＿＿＿]？""",
        ),
    ])

    # ========== 記述式シーディング Questions ==========
    db.add_all([
        models.Question(
            category_id=cat_free.id,
            customer_text="分割払いにしても月々の負担が大きいですよね。家賃とか生活費考えると厳しくて...",
            expected_points="共感→本質（今の収入では変わらない）→投資対効果→具体的な方法提示",
            difficulty="hard",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="貯金が少ないので、もう少し貯めてから始めようと思います",
            expected_points="共感→貯まらない理由の言語化→今始めることで変えられる未来提示",
            difficulty="easy",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="親に相談してみます。反対されるかもしれないけど、一応聞いてみないと",
            expected_points="共感→意欲確認→反対された場合の分岐→自分で決める大切さ",
            difficulty="normal",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="家族と話し合ってみてからにします。来週末に話す機会があるので",
            expected_points="共感→揺れるかどうか確認→山北さんトーク→次のアクション設定",
            difficulty="easy",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="○○社のサービスと比較してから決めたいです。そっちの方が安いみたいで",
            expected_points="比較肯定→価格以外の価値提示→信頼関係を戻す→不安の本質深掘り",
            difficulty="hard",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="ネットでいろいろ調べてみたら他にも似たようなサービスがあって迷っています",
            expected_points="共感→比較理由の深掘り→関係性戻し→今一番引っかかっていることの確認",
            difficulty="normal",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="今は繁忙期なので、落ち着いてからにしたいです。3ヶ月後くらいなら...",
            expected_points="共感→3ヶ月待つリスク言語化→いくみさんトーク→今ある時間の探し方",
            difficulty="normal",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="子育て中で、まとまった時間を作るのが難しいです。子供が小さいうちは...",
            expected_points="共感→子育て中でもできる理由→スキマ時間活用→具体的なスケジュール提案",
            difficulty="hard",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_free.id,
            customer_text="週末も予定が詰まっていて、いつやればいいのか見当もつかないです",
            expected_points="共感→時間は見つかるではなく作るもの→10分単位での棚卸し提案",
            difficulty="easy",
            fill_template=None,
        ),
    ])

    # ========== 音声入力シーディング Questions ==========
    db.add_all([
        models.Question(
            category_id=cat_voice.id,
            customer_text="毎月の固定費がかなり多くて、これ以上出費を増やすのは難しいんですよね",
            expected_points="共感→今の状態での投資対効果→はるかさんトーク→一緒に解決策を考えるクロージング",
            difficulty="normal",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_voice.id,
            customer_text="友達に話したら「大丈夫なの？」って心配されてしまって、なんか不安になってきました",
            expected_points="共感→友人の心配は愛情から→自分で決める大切さ→山北さんトーク活用",
            difficulty="normal",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_voice.id,
            customer_text="もう少し情報収集してから。今は比較検討中なので、もう少し時間をください",
            expected_points="比較肯定→情報収集の深掘り→まこさんトーク→今一番引っかかっている点の確認",
            difficulty="easy",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_voice.id,
            customer_text="今は引っ越し準備中で、バタバタしてて。落ち着いたらと思っているんですが...",
            expected_points="共感→いくみさんトーク→時間は作るもの→今できる範囲の提案",
            difficulty="easy",
            fill_template=None,
        ),
        models.Question(
            category_id=cat_voice.id,
            customer_text="やりたい気持ちはあるんですけど、パートナーが乗り気じゃなくて...",
            expected_points="共感→やりたい気持ち確認→山北さんトーク→自分で決断することの意味",
            difficulty="hard",
            fill_template=None,
        ),
    ])
    db.flush()

    # ========== Registered Cases (全カテゴリで使用) ==========
    haruka_story = """受講料大丈夫かな、とか、お金不安だなっていう気持ちもあると思うんですけど、全然その気持ち持ったままで大丈夫ですよ。

実は、前にはるかさんっていう医療事務で働かれてた方がいて、手取りが15万くらいで、そこから家賃とか生活費払ったらほとんど残らない状態だったんですよね。

その方も全く同じで、"お金が不安でどうしよう"ってすごく悩まれてて、最初は「もう少し貯金してからにしようかな」って言ってたんです。

ただその時に言ってたのが、"今の状況で貯金ができてないのに、貯めてからって言ってたら、いつになるか分からない"って。

もし1ヶ月で10万円でもプラスにできる可能性があるなら、今始めるのか1年後始めるのかで、120万円くらい差が出るかもしれないって考えたら、今やるしかないって思ったらしいんですよね。

それで"人生最後の貧乏だと思ってやります"って言って始められて、結果的に1年後には収入も増えてフリーランスになってました。

だから、不安がある状態で始めるのってすごく普通なんですけど、その中でも一歩踏み出した人が変わっていくんだなってすごく感じてます。

〇〇さん的に、もしやるとしたらなんですけど、今の状況の中でどうやったら進められそうか、一緒に考えてみてもいいですか？"""

    ikumi_story = """時間の不安、めちゃくちゃ分かります。実際に同じこと言われる方すごく多いです。

前にいくみさんっていう、イベント会社で照明のお仕事されてる方がいて、コンサートとかで地方行くので、1ヶ月家にいないとか、朝から夜終電まで働いてて、休みも月1日あるかどうかみたいな方だったんですよ。

正直、私も"それで本当に大丈夫ですか？時間取れますか？"って思ってたんですけど、その時いくみさんが言ってたのが"じゃあ時間できるのを待ちますって言っても、私には時間ができないんです"って。

で、じゃあ仕事辞めてからにするかってなると、今度はお金の不安が出てくるから、結局どのタイミングでも何かしらの不安はあるって言われてて。

だったら、今ある状況の中でできる方法を考えるしかないって言って始められたんですよね。

実際どうしてたかっていうと、1日のスケジュールをコーチと一緒に10分単位で全部洗い出したら、意外と空いてる時間とか、なんとなく使ってる時間が出てきて、そこを使って進めていったらしいんです。

結果的に、進捗率も200％超えてたって言ってて、その時に"時間ってできるものじゃなくて作るものなんだな"ってすごく感じました。

〇〇さんも、もしやるとしたらでいいんですけど、今の生活の中でどこなら少しでも時間作れそうか、一緒に見てみます？"""

    yamakita_story = """相談したいって思うの、すごく大事なことだと思いますし、心配になる気持ちもすごく分かります。

前に山北さんっていう方がいて、旦那さんに最初すごく反対されてたんですよね。やっぱり"お金大丈夫なの？"とか"時間取れるの？"って、心配から反対されるケースってすごく多くて。

その中で山北さんが言ってたのが、"結局自分の人生だから、自分で決めないと何も変わらない"って。

もしその時にやらなかったら、"あの時やっておけばよかったな"って絶対後悔するし、その時に旦那さんに反対されたからって人のせいにしてしまいそうだったって言ってて。それが嫌だったから、自分で決断して始められたらしいんです。

最初はやっぱり大変だったみたいなんですけど、結果が出てから旦那さんに初めて認めてもらえて、"あの時やってよかった"って言ってましたね。

なので、相談すること自体は全然いいと思うんですけど、〇〇さんとしては、やりたい気持ちとやりたくない気持ちだったら、どっちが強いですか？"""

    mako_story = """他社も見たいっていう気持ち、全然自然だと思います。

実際にまこさんっていう元看護師の方も、いろんなスクール見てた方だったんですよね。その方も彼氏さんに相談したら、"本当にできるの？"とか"時間取れるの？"ってかなり論理的に反対されたらしくて。

普通だったらそこで悩むと思うんですけど、まこさんが言ってたのが"やるのは自分だし、あの時やっておけばよかったって後悔するくらいならやる"って。

もし反対されたからやらないってなったら、後から絶対後悔するし、その時に人のせいにしてしまいそうだったって言ってて。だからこそ、自分で決めてやるっていう選択をしたらしいんですよね。

最初に案件取れた時に、めちゃくちゃ嬉しくて彼氏さんに報告したら、そこから応援してもらえるようになったって言ってました。

なので、比較すること自体は全然いいと思うんですけど、〇〇さんとしては、今一番引っかかってるポイントってどこですか？"""

    db.add_all([
        models.RegisteredCase(category_id=cat_fill.id, person_name="はるかさん", story_text=haruka_story, allowed=True),
        models.RegisteredCase(category_id=cat_fill.id, person_name="いくみさん", story_text=ikumi_story, allowed=True),
        models.RegisteredCase(category_id=cat_fill.id, person_name="山北さん", story_text=yamakita_story, allowed=True),
        models.RegisteredCase(category_id=cat_fill.id, person_name="まこさん", story_text=mako_story, allowed=True),
    ])

    db.commit()
    db.close()
    print("✅ データベースの初期化が完了しました。")
    print("   管理者: admin@example.com / admin123")
    print("   ユーザー: tanaka@example.com / test123")


if __name__ == "__main__":
    init()
