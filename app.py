import os, json, re
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from anthropic import Anthropic
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
_db_url = os.getenv('DATABASE_URL', 'sqlite:///seeding.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'seeding-secret-2024'),
    SQLALCHEMY_DATABASE_URI=_db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
)

db = SQLAlchemy(app)
CORS(app, supports_credentials=True)
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# ── Models ──────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    current_day = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email,
                'role': self.role, 'current_day': self.current_day}


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    emoji = db.Column(db.String(10), default='📖')

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'description': self.description, 'emoji': self.emoji}


class TalkTemplate(db.Model):
    __tablename__ = 'talk_templates'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    internal_case_name = db.Column(db.String(100))
    full_script = db.Column(db.Text, nullable=False)
    key_phrases = db.Column(db.Text)
    required_points = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'category_id': self.category_id,
            'display_name': self.display_name,
            'internal_case_name': self.internal_case_name,
            'full_script': self.full_script,
            'key_phrases': json.loads(self.key_phrases) if self.key_phrases else [],
            'required_points': json.loads(self.required_points) if self.required_points else [],
        }


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(50), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    talk_template_id = db.Column(db.Integer, db.ForeignKey('talk_templates.id'))
    question_type = db.Column(db.String(50))
    customer_text = db.Column(db.Text)
    prompt_text = db.Column(db.Text)
    correct_answer = db.Column(db.Text)
    choices = db.Column(db.Text)
    difficulty = db.Column(db.Integer, default=1)
    day = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'mode': self.mode, 'category_id': self.category_id,
            'talk_template_id': self.talk_template_id,
            'question_type': self.question_type,
            'customer_text': self.customer_text,
            'prompt_text': self.prompt_text,
            'correct_answer': self.correct_answer,
            'choices': json.loads(self.choices) if self.choices else None,
            'difficulty': self.difficulty, 'day': self.day,
        }


class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_text = db.Column(db.Text)
    score_total = db.Column(db.Integer, default=0)
    score_structure = db.Column(db.Integer, default=0)
    score_reproduction = db.Column(db.Integer, default=0)
    title = db.Column(db.String(50))
    is_passed = db.Column(db.Boolean, default=False)
    has_compliance_ng = db.Column(db.Boolean, default=False)
    compliance_ng_words = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='answers')
    question = db.relationship('Question', backref='answers')

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'question_id': self.question_id,
            'answer_text': self.answer_text, 'score_total': self.score_total,
            'score_structure': self.score_structure,
            'score_reproduction': self.score_reproduction,
            'title': self.title, 'is_passed': self.is_passed,
            'has_compliance_ng': self.has_compliance_ng,
            'compliance_ng_words': json.loads(self.compliance_ng_words) if self.compliance_ng_words else [],
            'ai_feedback': json.loads(self.ai_feedback) if self.ai_feedback else None,
            'created_at': self.created_at.isoformat(),
        }


class AdminComment(db.Model):
    __tablename__ = 'admin_comments'
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=False)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin_user = db.relationship('User', foreign_keys=[admin_user_id])
    answer = db.relationship('Answer', backref='comments')

    def to_dict(self):
        return {
            'id': self.id, 'answer_id': self.answer_id,
            'admin_name': self.admin_user.name if self.admin_user else None,
            'comment': self.comment,
            'created_at': self.created_at.isoformat(),
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'ログインが必要です'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'ログインが必要です'}), 401
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': '管理者権限が必要です'}), 403
        return f(*args, **kwargs)
    return decorated


def score_to_title(score):
    if score is None: return '練習スタート'
    if score <= 59: return '練習スタート'
    if score <= 69: return '見習い営業'
    if score <= 79: return 'あと少し'
    if score <= 89: return '現場OK'
    if score <= 99: return '即決メーカー'
    return 'シーディングマスター'


def get_mode_progress(user_id, category_id):
    result = {}
    quick_best = 0
    repro_best = 0
    for mode in ['quick', 'reproduction', 'simulation']:
        answers = (Answer.query
                   .join(Question, Question.id == Answer.question_id)
                   .filter(Answer.user_id == user_id,
                           Question.category_id == category_id,
                           Question.mode == mode).all())
        best = max((a.score_total for a in answers), default=None)
        count = len(answers)
        result[mode] = {'best_score': best, 'count': count}
        if mode == 'quick': quick_best = best or 0
        if mode == 'reproduction': repro_best = best or 0

    result['quick']['unlocked'] = True
    result['reproduction']['unlocked'] = quick_best >= 80
    result['simulation']['unlocked'] = repro_best >= 80
    return result


# ── Talk Scripts ──────────────────────────────────────────────────────────────

HARUKA_SCRIPT = """受講料大丈夫かな、とか、お金不安だなっていう気持ちもあると思うんですけど、全然その気持ち持ったままで大丈夫ですよ。

実は、前にはるかさんっていう医療事務で働かれてた方がいて、手取りが15万くらいで、そこから家賃とか生活費払ったらほとんど残らない状態だったんですよね。

その方も全く同じで、"お金が不安でどうしよう"ってすごく悩まれてて、最初は「もう少し貯金してからにしようかな」って言ってたんです。

ただその時に言ってたのが、"今の状況で貯金ができてないのに、貯めてからって言ってたら、いつになるか分からない"って。

もし1ヶ月で10万円でもプラスにできる可能性があるなら、今始めるのか1年後始めるのかで、120万円くらい差が出るかもしれないって考えたら、今やるしかないって思ったらしいんですよね。

それで"人生最後の貧乏だと思ってやります"って言って始められて、結果的に1年後には収入も増えてフリーランスになってました。

だから、不安がある状態で始めるのってすごく普通なんですけど、その中でも一歩踏み出した人が変わっていくんだなってすごく感じてます。

〇〇さん的に、もしやるとしたらなんですけど、今の状況の中でどうやったら進められそうか、一緒に考えてみてもいいですか？"""

IKUMI_SCRIPT = """時間の不安、めちゃくちゃ分かります。実際に同じこと言われる方すごく多いです。

前にいくみさんっていう、イベント会社で照明のお仕事されてる方がいて、コンサートとかで地方行くので、1ヶ月家にいないとか、朝から夜終電まで働いてて、休みも月1日あるかどうかみたいな方だったんですよ。

正直、私も"それで本当に大丈夫ですか？時間取れますか？"って思ってたんですけど、その時いくみさんが言ってたのが、"じゃあ時間できるのを待ちますって言っても、私には時間ができないんです"って。

で、じゃあ仕事辞めてからにするかってなると、今度はお金の不安が出てくるから、結局どのタイミングでも何かしらの不安はあるって言われてて。

だったら、今ある状況の中でできる方法を考えるしかないって言って始められたんですよね。

実際どうしてたかっていうと、1日のスケジュールをコーチと一緒に10分単位で全部洗い出したら、意外と空いてる時間とか、なんとなく使ってる時間が出てきて、そこを使って進めていったらしいんです。

結果的に、進捗率も200%超えてたって言ってて、その時に"時間ってできるものじゃなくて作るものなんだな"ってすごく感じました。

〇〇さんも、もしやるとしたらでいいんですけど、今の生活の中でどこなら少しでも時間作れそうか、一緒に見てみます？"""

YAMAKITA_SCRIPT = """旦那さんに、最初は反対されてたみたいで。やっぱり一番応援してほしい人に反対されるのって、正直かなりしんどいじゃないですか。

私も旦那さんの気持ちはすごく分かって。反対というより、「心配」ですよね。これから子どもにもお金かかるのに大丈夫？とか、ただでさえ忙しいのに本当に続けられるの？とか。

でも山北さんは、「結局、自分の人生だからやらないと何も変わらない」っていうところで、始められたんですよね。

何より印象的だったのが、「旦那さんに反対されたからできなかった」っていう理由を、絶対に作りたくなかったっていう話で。

もしあの時やらなくて、後から「あの時やっておけばよかったな」って思った時に、絶対後悔するし、旦那さんのせいにしてしまう気がしたらしくて。

それが嫌だったから、後悔しない選択をしたって言ってました。

実際、忙しい中でも時間を作って頑張って、40時間で5万円プラスの収益が出てるんですよね。

その収益で、旦那さんとお子さんを連れてご飯に行ったらしいんですけど、その時に初めて「すごく頑張ったね」って認めてもらえたらしくて。

それが一番嬉しかったって言ってました。

「こんなことなら結果出てから言えばよかった〜（笑）」とも言ってましたけどね😂

〇〇さん、聞いてみてどう思いましたか？"""

MAKO_SCRIPT = """他社も見たいっていう気持ち、全然自然だと思います。

実際にまこさんっていう元看護師の方も、いろんなスクール見てた方だったんですよね。

その方も彼氏さんに相談したら、"本当にできるの？"とか"時間取れるの？"ってかなり論理的に反対されたらしくて。

普通だったらそこで悩むと思うんですけど、まこさんが言ってたのが、"やるのは自分だし、あの時やっておけばよかったって後悔するくらいならやる"って。

もし反対されたからやらないってなったら、後から絶対後悔するし、その時に人のせいにしてしまいそうだったって言ってて。

だからこそ、自分で決めてやるっていう選択をしたらしいんですよね。

最初に案件取れた時に、めちゃくちゃ嬉しくて彼氏さんに報告したら、そこから応援してもらえるようになったって言ってました。

なので、比較すること自体は全然いいと思うんですけど、〇〇さんとしては、今一番引っかかってるポイントってどこですか？"""


# ── Seed ─────────────────────────────────────────────────────────────────────

def seed_db():
    if Category.query.count() > 0:
        seed_additional_questions()
        return

    cats = [
        Category(id=1, name='金額渋りトーク', description='お金の不安をなくし、価値を伝えて前に進む！', emoji='💰'),
        Category(id=2, name='時間渋りトーク', description='忙しくても時間は作れる！行動できる未来へ導く！', emoji='⏰'),
        Category(id=3, name='相談渋りトーク', description='大切な人の意見も大事にしながら、自分の未来を自分で決める！', emoji='💬'),
        Category(id=4, name='他社比較渋りトーク', description='他社と比べる不安を解消し、あなたに合う選択をサポート！', emoji='⚖️'),
    ]
    db.session.add_all(cats)

    kp1 = json.dumps(["今の状況で貯金ができてないのに、貯めてからって言ってたら、いつになるか分からない","120万円くらい差が出るかもしれない","人生最後の貧乏だと思ってやります","一緒に考えてみてもいいですか"], ensure_ascii=False)
    rp1 = json.dumps(["共感・受け入れから始める","はるかさんの実例を使う（医療事務、手取り15万）","具体的な数字を入れる（120万円）","最後は質問で締める"], ensure_ascii=False)
    kp2 = json.dumps(["時間ってできるものじゃなくて作るものなんだな","10分単位で全部洗い出したら","進捗率も200%超えてた","一緒に見てみます"], ensure_ascii=False)
    rp2 = json.dumps(["共感から始める","いくみさんの実例を使う（イベント会社・照明・月1日休み）","「時間は作るもの」というキーフレーズを入れる","最後は一緒に考える提案で締める"], ensure_ascii=False)
    kp3 = json.dumps(["結局、自分の人生だからやらないと何も変わらない","旦那さんに反対されたからできなかった」っていう理由を、絶対に作りたくなかった","あの時やっておけばよかったな","後悔しない選択をした","40時間で5万円プラスの収益"], ensure_ascii=False)
    rp3 = json.dumps(["一番応援してほしい人に反対されるしんどさに共感する","反対を「心配」として捉え直す","山北さんの実例を使う（旦那さんに反対された）","自分で決断することの大切さを伝える（後悔しない選択）","具体的な成果を伝える（40時間で5万円）"], ensure_ascii=False)
    kp4 = json.dumps(["やるのは自分だし、後悔するくらいならやる","人のせいにしてしまいそうだった","今一番引っかかってるポイントってどこですか"], ensure_ascii=False)
    rp4 = json.dumps(["比較したい気持ちに共感する","まこさんの実例を使う（元看護師・彼氏に反対された）","自分で決める大切さを伝える","最後は引っかかっているポイントを確認する質問で締める"], ensure_ascii=False)

    templates = [
        TalkTemplate(id=1, category_id=1, display_name='金額渋りトーク', internal_case_name='はるかさんトーク', full_script=HARUKA_SCRIPT, key_phrases=kp1, required_points=rp1),
        TalkTemplate(id=2, category_id=2, display_name='時間渋りトーク', internal_case_name='いくみさんトーク', full_script=IKUMI_SCRIPT, key_phrases=kp2, required_points=rp2),
        TalkTemplate(id=3, category_id=3, display_name='相談渋りトーク', internal_case_name='山北さんトーク', full_script=YAMAKITA_SCRIPT, key_phrases=kp3, required_points=rp3),
        TalkTemplate(id=4, category_id=4, display_name='他社比較渋りトーク', internal_case_name='まこさんトーク', full_script=MAKO_SCRIPT, key_phrases=kp4, required_points=rp4),
    ]
    db.session.add_all(templates)

    steps1 = json.dumps(["①共感・受け入れ", "②はるかさんの実例紹介", "③数字で訴求（120万円）", "④質問で締める"], ensure_ascii=False)
    steps2 = json.dumps(["①共感・受け入れ", "②いくみさんの実例紹介", "③時間は作るもの", "④一緒に考える提案"], ensure_ascii=False)
    steps3 = json.dumps(["①共感・受け入れ", "②山北さんの実例紹介", "③自分で決める大切さ", "④やりたい気持ちを確認"], ensure_ascii=False)
    steps4 = json.dumps(["①共感・受け入れ", "②まこさんの実例紹介", "③後悔しない選択", "④引っかかりを確認"], ensure_ascii=False)

    questions = _base_questions(steps1, steps2, steps3, steps4) + _additional_questions()
    db.session.add_all(questions)
    db.session.add(User(name='管理者', email='admin@seeding.app', role='admin'))
    db.session.commit()
    print('✅ データベースのシード完了')


def _base_questions(steps1, steps2, steps3, steps4):
    return [
        # ── DAY1 金額渋り ──
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='今の状況で【　　】ができてないのに、貯めてからって言ってたら、いつになるか分からない', prompt_text='【　　】に入る言葉は？', correct_answer='貯金', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='今始めるのか1年後始めるのかで、【　　】万円くらい差が出るかもしれない', prompt_text='【　　】に入る数字は？', correct_answer='120', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='【　　】な貧乏だと思ってやります', prompt_text='【　　】に入る言葉は？', correct_answer='人生最後', difficulty=2),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='今の状況の中でどうやったら進められそうか、【　　】考えてみてもいいですか？', prompt_text='【　　】に入る言葉は？', correct_answer='一緒に', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='reorder', prompt_text='はるかさんトークの流れを正しい順に並べてください', choices=json.dumps(["③数字で訴求（120万円）", "①共感・受け入れ", "④質問で締める", "②はるかさんの実例紹介"], ensure_ascii=False), correct_answer=steps1, difficulty=2),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='model_check', prompt_text='模範トークを読んで内容を確認しましょう', difficulty=1),
        # ── DAY1 時間渋り ──
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='時間ってできるものじゃなくて【　　】ものなんだな', prompt_text='【　　】に入る言葉は？', correct_answer='作る', difficulty=1),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='1日のスケジュールをコーチと一緒に【　　】単位で全部洗い出したら', prompt_text='【　　】に入る言葉は？', correct_answer='10分', difficulty=1),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='進捗率も【　　】%超えてたって言ってて', prompt_text='【　　】に入る数字は？', correct_answer='200', difficulty=2),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='今の生活の中でどこなら少しでも時間作れそうか、【　　】見てみます？', prompt_text='【　　】に入る言葉は？', correct_answer='一緒に', difficulty=1),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='reorder', prompt_text='いくみさんトークの流れを正しい順に並べてください', choices=json.dumps(["③時間は作るもの", "①共感・受け入れ", "④一緒に考える提案", "②いくみさんの実例紹介"], ensure_ascii=False), correct_answer=steps2, difficulty=2),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='model_check', prompt_text='模範トークを読んで内容を確認しましょう', difficulty=1),
        # ── DAY1 相談渋り ──
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='結局【　　】の人生だから、自分で決めないと何も変わらない', prompt_text='【　　】に入る言葉は？', correct_answer='自分', difficulty=1),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='旦那さんに反対されたからって【　　】のせいにしてしまいそうだった', prompt_text='【　　】に入る言葉は？', correct_answer='人', difficulty=1),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='やりたい気持ちとやりたくない気持ちだったら、【　　】が強いですか？', prompt_text='【　　】に入る言葉は？', correct_answer='どっち', difficulty=2),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='reorder', prompt_text='山北さんトークの流れを正しい順に並べてください', choices=json.dumps(["③自分で決める大切さ", "①共感・受け入れ", "④やりたい気持ちを確認", "②山北さんの実例紹介"], ensure_ascii=False), correct_answer=steps3, difficulty=2),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='model_check', prompt_text='模範トークを読んで内容を確認しましょう', difficulty=1),
        # ── DAY1 他社比較渋り ──
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='やるのは【　　】だし、後悔するくらいならやる', prompt_text='【　　】に入る言葉は？', correct_answer='自分', difficulty=1),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='後から絶対後悔するし、その時に【　　　】にしてしまいそうだった', prompt_text='【　　　】に入る言葉は？', correct_answer='人のせい', difficulty=2),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='今一番引っかかってる【　　】ってどこですか？', prompt_text='【　　】に入る言葉は？', correct_answer='ポイント', difficulty=1),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='reorder', prompt_text='まこさんトークの流れを正しい順に並べてください', choices=json.dumps(["③後悔しない選択", "①共感・受け入れ", "④引っかかりを確認", "②まこさんの実例紹介"], ensure_ascii=False), correct_answer=steps4, difficulty=2),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='model_check', prompt_text='模範トークを読んで内容を確認しましょう', difficulty=1),
        # ── DAY2 再現チャレンジ ──
        Question(day=2, mode='reproduction', category_id=1, talk_template_id=1, question_type='free_text', customer_text='受講料を見たんですけど、やっぱり金額が高くて…正直お金の不安がある状態では難しいかもしれません', prompt_text='金額渋りトーク（はるかさんトーク）を使って回答してください', difficulty=2),
        Question(day=2, mode='reproduction', category_id=2, talk_template_id=2, question_type='free_text', customer_text='時間がなくて忙しくて、続けられるか不安です。仕事もあるし、正直いつ勉強するかも分からなくて', prompt_text='時間渋りトーク（いくみさんトーク）を使って回答してください', difficulty=2),
        Question(day=2, mode='reproduction', category_id=3, talk_template_id=3, question_type='free_text', customer_text='気持ちはあるんですけど、夫に相談してから決めたいと思って。反対されたら難しいかもしれないし', prompt_text='相談渋りトーク（山北さんトーク）を使って回答してください', difficulty=2),
        Question(day=2, mode='reproduction', category_id=4, talk_template_id=4, question_type='free_text', customer_text='いろんなスクールを比較してから決めたいんですよね。もう少し他も見てみようかなと思っていて', prompt_text='他社比較渋りトーク（まこさんトーク）を使って回答してください', difficulty=2),
        # ── DAY3 実戦シミュレーション ──
        Question(day=3, mode='simulation', category_id=1, talk_template_id=1, question_type='free_text', customer_text='時間もないし、お金の不安もあって…どうしようかなって思っています', prompt_text='複合渋り（時間＋金額）に対応してください。適切なトークを組み合わせて回答しましょう', difficulty=3),
        Question(day=3, mode='simulation', category_id=3, talk_template_id=3, question_type='free_text', customer_text='主人に相談したいのと、他のスクールも見てみたいんですよね。今すぐっていうのはちょっと', prompt_text='複合渋り（相談＋他社比較＋今じゃない）に対応してください。適切なトークを組み合わせて回答しましょう', difficulty=3),
    ]


def _additional_questions():
    return [
        # ── 金額渋り 追加穴埋め ──
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='前にはるかさんっていう【　　　】で働かれてた方がいて', prompt_text='【　　　】に入る職業は？', correct_answer='医療事務', difficulty=2),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='手取りが【　　】くらいで、そこから家賃とか生活費払ったらほとんど残らない状態', prompt_text='【　　】に入る金額は？', correct_answer='15万', difficulty=2),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='結果的に【　　】後には収入も増えてフリーランスになってました', prompt_text='【　　】に入る期間は？', correct_answer='1年', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='【　　】がある状態で始めるのってすごく普通なんですけど', prompt_text='【　　】に入る言葉は？', correct_answer='不安', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='もう少し【　　】してからにしようかなって言ってたんです', prompt_text='【　　】に入る言葉は？', correct_answer='貯金', difficulty=1),
        Question(day=1, mode='quick', category_id=1, talk_template_id=1, question_type='fill_blank', customer_text='その中でも一歩【　　】した人が変わっていくんだなってすごく感じてます', prompt_text='【　　】に入る言葉は？', correct_answer='踏み出', difficulty=2),
        # ── 時間渋り 追加穴埋め ──
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='1ヶ月【　　】にいないとか、朝から夜終電まで働いてて', prompt_text='【　　】に入る場所は？', correct_answer='家', difficulty=1),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='じゃあ仕事【　　　　】にするかってなると、今度はお金の不安が出てくる', prompt_text='【　　　　】に入る言葉は？', correct_answer='辞めてから', difficulty=2),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='結局どの【　　　　】でも何かしらの不安はあるって言われてて', prompt_text='【　　　　】に入る言葉は？', correct_answer='タイミング', difficulty=2),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='意外と空いてる時間とか、なんとなく【　　　】時間が出てきて', prompt_text='【　　　】に入る言葉は？', correct_answer='使ってる', difficulty=2),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='じゃあ時間できるのを待ちますって言っても、私には時間が【　　　　　】んです', prompt_text='【　　　　　】に入る言葉は？', correct_answer='できない', difficulty=1),
        Question(day=1, mode='quick', category_id=2, talk_template_id=2, question_type='fill_blank', customer_text='今ある状況の中でできる【　　　】を考えるしかないって言って始められた', prompt_text='【　　　】に入る言葉は？', correct_answer='方法', difficulty=1),
        # ── 相談渋り 追加穴埋め ──
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='旦那さんに最初すごく【　　】されてたんですよね', prompt_text='【　　】に入る言葉は？', correct_answer='反対', difficulty=1),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='心配から【　　】されるケースってすごく多くて', prompt_text='【　　】に入る言葉は？', correct_answer='反対', difficulty=1),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='【　　】が出てから旦那さんに初めて認めてもらえて', prompt_text='【　　】に入る言葉は？', correct_answer='結果', difficulty=1),
        Question(day=1, mode='quick', category_id=3, talk_template_id=3, question_type='fill_blank', customer_text='あの時に【　　　　　　　】って絶対後悔するし、人のせいにしてしまいそうだった', prompt_text='【　　　　　　　】に入る言葉は？', correct_answer='やっておけばよかったな', difficulty=2),
        # ── 他社比較渋り 追加穴埋め ──
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='実際にまこさんっていう【　　　】の方も、いろんなスクール見てた方だったんですよね', prompt_text='【　　　】に入る職業は？', correct_answer='元看護師', difficulty=2),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='"本当にできるの？"とか"時間取れるの？"ってかなり【　　】に反対されたらしくて', prompt_text='【　　】に入る言葉は？', correct_answer='論理的', difficulty=2),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='最初に【　　】取れた時に、めちゃくちゃ嬉しくて彼氏さんに報告したら', prompt_text='【　　】に入る言葉は？', correct_answer='案件', difficulty=2),
        Question(day=1, mode='quick', category_id=4, talk_template_id=4, question_type='fill_blank', customer_text='比較すること自体は全然いいと思うんですけど、今一番【　　　　　　　　　　】ってどこですか？', prompt_text='【　　　　　　　　　　】に入る言葉は？', correct_answer='引っかかってるポイント', difficulty=2),
    ]


def seed_additional_questions():
    existing = {q.customer_text for q in Question.query.all()}
    added = 0
    for q in _additional_questions():
        if q.customer_text not in existing:
            db.session.add(q)
            added += 1
    if added:
        db.session.commit()
        print(f'✅ {added}問追加しました')


# ── AI Scoring ────────────────────────────────────────────────────────────────

# ── Fill-blank phrase reasons ─────────────────────────────────────────────────

PHRASE_REASONS = {
    '今の状況で【　　】ができてないのに、貯めてからって言ってたら、いつになるか分からない':
        '先延ばしの矛盾を自分で気づかせる言葉。"今貯金できていない"のに「もっと貯めてから」と言っていては、永遠に始められないことに気づかせます。',
    '今始めるのか1年後始めるのかで、【　　】万円くらい差が出るかもしれない':
        '具体的な数字（120万円）で先延ばしのコストを可視化。お金の不安を「だから行動しない」ではなく「だから今動く」という理由に変換するトークの核心です。',
    '【　　】な貧乏だと思ってやります':
        'はるかさんが覚悟を決めた瞬間の言葉。この一言が第三者事例に説得力を与え、「自分も同じ気持ちで始めていい」という心理的な許可をお客様に与えます。',
    '今の状況の中でどうやったら進められそうか、【　　】考えてみてもいいですか？':
        '"一緒に"という言葉が押しつけでなく寄り添う姿勢を示します。クロージングを質問で終えることで、お客様が主体的に考えられる空間を作ります。',
    '時間ってできるものじゃなくて【　　】ものなんだな':
        'このトーク全体のメッセージを一言で凝縮したキーフレーズ。「時間ができるまで待つ」という受け身の姿勢から、「時間を作る」という能動的な意識転換を促します。',
    '1日のスケジュールをコーチと一緒に【　　】単位で全部洗い出したら':
        '"10分単位"という具体性が、時間の使い方を可視化する方法をリアルにイメージさせます。「時間がない」という漠然とした不安を、具体的な解決策に変えます。',
    '進捗率も【　　】%超えてたって言ってて':
        '"200%超え"という驚きの数字がインパクトを与えます。「あれほど忙しい人でも成果が出た」という事実が、「自分には無理」という思い込みを崩します。',
    '今の生活の中でどこなら少しでも時間作れそうか、【　　】見てみます？':
        '"一緒に見てみる"という提案でお客様を孤立させません。「あなたと一緒に考える」という姿勢を示す、寄り添いのクロージングです。',
    '旦那さんに反対されたからって【　　】のせいにしてしまいそうだった':
        '"人のせいにしたくない"という心理を活用した言葉。他者の反対で諦めることが「後で誰かのせいにする」ことと同義だと気づかせ、自己決断の大切さを引き出します。',
    'やりたい気持ちとやりたくない気持ちだったら、【　　】が強いですか？':
        'クロージングの核心となる質問。お客様自身に「やりたい」という気持ちを言語化させることで、背中を押すのではなく本人から行動の意志を引き出します。',
    'やるのは【　　】だし、後悔するくらいならやる':
        '"やるのは自分"という言葉で、他者の意見より自分の意志を優先させます。比較という行為の主体が自分であり、最終的に決めるのも自分だという意識を引き出します。',
    '後から絶対後悔するし、その時に【　　　】にしてしまいそうだった':
        '"人のせいにしたくない"という本能的な心理を活用。他社比較をやめて自分で決める動機づけになる言葉です。',
    '今一番引っかかってる【　　】ってどこですか？':
        '"一番引っかかっているポイント"を特定する質問。漠然とした「他も見たい」という不安を具体的な問題に変換し、解決できる状態に持っていくクロージングです。',
    '前にはるかさんっていう【　　　】で働かれてた方がいて':
        '具体的な職業名を言うことで、事例のリアリティが格段に上がります。"どこかの誰か"ではなく"医療事務で働いていた人"という具体性が共感を生みます。',
    '手取りが【　　】くらいで、そこから家賃とか生活費払ったらほとんど残らない状態':
        '具体的な金額（15万円）で状況の厳しさをリアルに伝えます。「自分と同じような状況の人がいた」と感じることで、事例が他人事でなくなります。',
    '結果的に【　　】後には収入も増えてフリーランスになってました':
        '"1年後"という具体的な期間が、現実的な未来像をイメージさせます。長すぎず短すぎない期間で「自分にも達成できるかも」という希望につながります。',
    '【　　】がある状態で始めるのってすごく普通なんですけど':
        '"不安があって当然"という共感がお客様の心理的ハードルを下げます。不安を否定せず受け入れることが共感の第一歩。「不安があるからやめる」という思考パターンを崩します。',
    'もう少し【　　】してからにしようかな':
        '多くのお客様が口にする先延ばしの典型パターン。はるかさんも同じことを言っていたという事実が「自分だけじゃない」という共感と、「それでも乗り越えた」という希望を同時に伝えます。',
    'その中でも一歩【　　】した人が変わっていくんだなってすごく感じてます':
        'トークの締めとなる大切な言葉。どれだけ良い話をしても"行動した人だけが変わる"というメッセージで、最後の背中を押します。',
    '1ヶ月【　　　　】にいないとか、朝から夜終電まで働いてて':
        '"1ヶ月家にいない"という極端な多忙さが説得力を生みます。「自分より忙しい人でも始められた」という事実が、お客様の「自分には無理」という言い訳を崩します。',
    'じゃあ仕事【　　　　】にするかってなると、今度はお金の不安が出てくる':
        '「仕事を辞めてから」という選択肢の問題点を示します。時間の不安を解消しようとすると別の不安が生まれるジレンマを言語化し、「今の状況でやるしかない」という気づきに導きます。',
    '結局どの【　　　　】でも何かしらの不安はあるって言われてて':
        '"完璧なタイミングはない"という核心的なメッセージ。いつでも何かしら不安はあるという現実を認めることで、「不安がなくなったら始めよう」という思考パターンを崩します。',
    '意外と空いてる時間とか、なんとなく【　　　】時間が出てきて':
        '"意識せず使っている時間"の存在に気づかせる言葉。「時間がない」と思っていても、使い方次第で時間が生まれることをリアルにイメージさせます。',
    'じゃあ時間できるのを待ちますって言っても、私には時間が【　　　　　】んです':
        'いくみさん本人の言葉。"待っていても時間は来ない"という現実直視が行動のきっかけになります。受け身ではなく能動的に行動する必要性を自らの言葉で伝える強い事例です。',
    '今ある状況の中でできる【　　　】を考えるしかないって言って始められた':
        '"与えられた状況の中で工夫する"という姿勢を示します。「環境が整ったら始める」から「今ある環境でできる方法を探す」という思考シフトを促す重要な言葉です。',
    '旦那さんに最初すごく【　　】されてたんですよね':
        '山北さんが最初から反対されていたという事実が共感を生みます。「最初は反対されても乗り越えられる」という前例を示すことで、相談渋りを持つお客様に希望を与えます。',
    '心配から【　　】されるケースってすごく多くて':
        '反対されることが"心配からくる愛情"であると伝える言葉。反対意見を否定せず受け入れることで、お客様の心理的防衛を解きます。',
    '【　　】が出てから旦那さんに初めて認めてもらえて':
        '"結果が出てから認めてもらえた"という展開が、先に行動することの価値を示します。相談して許可を得てから始めるより、行動して成果を見せる方が信頼を得られるというメッセージです。',
    'あの時に【　　　　　　　】って絶対後悔するし、人のせいにしてしまいそうだった':
        '「やっておけばよかった」という後悔を未来視点で語る言葉。行動しない選択のリスクを感情的にリアルにイメージさせ、今動く動機づけになります。',
    '実際にまこさんっていう【　　　】の方も、いろんなスクール見てた方だったんですよね':
        '具体的な職業（元看護師）を言うことで事例のリアリティが増します。医療職という高スキルな職業の人も比較していたという事実が「自分だけじゃない」という共感を生みます。',
    '"本当にできるの？"とか"時間取れるの？"ってかなり【　　】に反対されたらしくて':
        '"論理的に反対された"という表現が、単なる感情的な反対より説得力のある懸念があったことを示します。それでも乗り越えたという事実が事例の強さになります。',
    '最初に【　　】取れた時に、めちゃくちゃ嬉しくて彼氏さんに報告したら':
        '"最初の案件が取れた"という具体的な成果が、始めることの価値を証明します。成果が出た瞬間の喜びを共有することで、お客様にも同じ未来をイメージさせます。',
    '比較すること自体は全然いいと思うんですけど、今一番【　　　　　　　　　　】ってどこですか？':
        '比較を否定せず受け入れた上で、核心的な懸念を特定する質問。「全部見てから決めたい」という漠然とした不安を「この点が解消されれば決められる」という具体的な状態に変えます。',
}


# シミュレーション複合問題: customer_text → 使用テンプレートIDリスト
SIMULATION_MULTI_TEMPLATES = {
    '主人に相談したいのと、他のスクールも見てみたいんですよね。今すぐっていうのはちょっと': [3, 4],
    '時間もないし、お金の不安もあって…どうしようかなって思っています': [1, 2],
}


def update_templates():
    """既存DBのテンプレートスクリプトを最新内容に更新する"""
    kp3 = json.dumps(["結局、自分の人生だからやらないと何も変わらない","旦那さんに反対されたからできなかった」っていう理由を、絶対に作りたくなかった","あの時やっておけばよかったな","後悔しない選択をした","40時間で5万円プラスの収益"], ensure_ascii=False)
    rp3 = json.dumps(["一番応援してほしい人に反対されるしんどさに共感する","反対を「心配」として捉え直す","山北さんの実例を使う（旦那さんに反対された）","自分で決断することの大切さを伝える（後悔しない選択）","具体的な成果を伝える（40時間で5万円）"], ensure_ascii=False)
    t3 = TalkTemplate.query.get(3)
    if t3:
        t3.full_script = YAMAKITA_SCRIPT
        t3.key_phrases = kp3
        t3.required_points = rp3
        db.session.commit()


def extract_context(full_script, customer_text):
    """スクリプトから穴埋め問題の前後の文脈（段落）を抽出する"""
    if not full_script or not customer_text:
        return None
    clean = re.sub(r'【[^】]*】', '', customer_text).strip()
    if not clean or len(clean) < 4:
        return None
    paragraphs = [p.strip() for p in re.split(r'\n\n+', full_script) if p.strip()]
    for key_len in range(min(14, len(clean)), 5, -2):
        for start in range(0, len(clean) - key_len + 1, 3):
            key = clean[start:start + key_len]
            for para in paragraphs:
                if key in para:
                    return para
    return None


def ai_score(mode, category_name, customer_text, talk_display_name, full_script, key_phrases, required_points, answer_text):
    sys_prompt = """あなたは営業トークの採点AIです。
新人営業がプレ即決率を上げるためのシーディングトークを、現場で使いこなせるようにすることが目的です。

【重要方針】
- 丸暗記ではなく「目的・意図を理解してトークを打てているか」を最重要評価軸にする
- トークの核心（共感→第三者事例→自己決断の促し→質問）の流れが伝わっているかを重視する
- 言葉が多少違っても、お客様の不安を受け止めて前向きに導けていれば高評価
- 模範スクリプトの丸コピーでも、意図を理解して使えていれば評価する（ただし棒読み感がある場合は指摘）
- 平均営業が70点を取れる基準にする
- フィードバックは新人営業が次に直せる具体的な言葉で出す
- コンプライアンスNGは減点する（1件につき-30点）
- 成果保証・圧迫・断定表現は厳しく評価する
- 実在事例ベースの第三者トークを高く評価する
- 最後は自然な質問で終わっているかを評価する"""

    user_prompt = f"""以下の営業回答を採点してください。

【モード】{mode}
【カテゴリ】{category_name}
【カウンセラーへの発言】{customer_text}
【指定トーク】{talk_display_name}
【模範スクリプト（参考）】
{full_script}
【必須要素（意図・目的として押さえるべきポイント）】{json.dumps(required_points, ensure_ascii=False)}
【キーフレーズ例（言葉より意味が伝わっているかを重視）】{json.dumps(key_phrases, ensure_ascii=False)}
【ユーザー回答】
{answer_text}

【採点基準】100点満点
意図・目的の理解度60点：
  相手の不安への共感・受け入れ（12点）、
  伝えたいことの本質の言語化（12点）、
  第三者事例を使って説得力を出せているか（12点）、
  相手が前向きになれる未来提示・行動の正当化（12点）、
  最後に相手に考えさせる質問で締めているか（12点）
トーク再現の完成度40点：
  この渋りカテゴリに合ったトーク内容か（8点）、
  話の流れが自然で伝わりやすいか（8点）、
  必須キーフレーズの意味が伝わっているか（8点）、
  具体的なエピソードが含まれているか（8点）、
  最後が質問で終わっているか（8点）

コンプライアンスNG（含む場合-30点/件）：絶対稼げます、元取れます、やるべき、やらないと損、強制・圧迫表現、成果保証表現

【出力形式】必ずJSONのみで返してください：
{{"score_total":数値,"is_passed":真偽,"score_structure":数値,"score_reproduction":数値,"has_compliance_ng":真偽,"compliance_ng_words":[],"structure_detail":{{"empathy":数値,"essence":数値,"third_party":数値,"future":数値,"closing":数値}},"reproduction_detail":{{"category_match":数値,"flow":数値,"key_phrases":数値,"episode":数値,"closing_question":数値}},"good_points":["良かった点"],"improvement_points":["改善点"],"missing_key_phrases":["意図が伝わっていなかった要素"],"safe_rewrite":"","ideal_answer":"理想のトーク例（150字程度）"}}"""

    resp = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=2000,
        system=sys_prompt,
        messages=[{'role': 'user', 'content': user_prompt}],
    )
    text = resp.content[0].text
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        raise ValueError('AIレスポンスのJSON解析に失敗しました')
    result = json.loads(m.group())
    result['title'] = score_to_title(result.get('score_total', 0))
    return result


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    if not name or not email:
        return jsonify({'error': '名前とメールアドレスを入力してください'}), 400
    user = User.query.filter_by(email=email).first()
    if user:
        session['user_id'] = user.id
        return jsonify({'user': user.to_dict(), 'message': 'ログインしました'})
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({'user': user.to_dict(), 'message': '登録完了しました'})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = (data.get('email') or '').strip()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'メールアドレスが見つかりません'}), 404
    session['user_id'] = user.id
    return jsonify({'user': user.to_dict()})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'ログアウトしました'})


@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({'error': 'ログインが必要です'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'ユーザーが見つかりません'}), 404
    return jsonify({'user': user.to_dict()})


@app.route('/api/home')
@login_required
def home():
    user = User.query.get(session['user_id'])
    latest = Answer.query.filter_by(user_id=user.id).order_by(Answer.created_at.desc()).first()
    latest_score = latest.score_total if latest else None
    total_answers = Answer.query.filter_by(user_id=user.id).count()
    return jsonify({
        'user': user.to_dict(),
        'latest_score': latest_score,
        'title': score_to_title(latest_score),
        'current_day': user.current_day,
        'total_answers': total_answers,
    })


@app.route('/api/categories')
@login_required
def get_categories():
    user_id = session['user_id']
    cats = Category.query.all()
    result = []
    for c in cats:
        progress = get_mode_progress(user_id, c.id)
        d = c.to_dict()
        d['progress'] = progress
        result.append(d)
    return jsonify({'categories': result})


@app.route('/api/progress/<int:category_id>')
@login_required
def get_progress(category_id):
    progress = get_mode_progress(session['user_id'], category_id)
    return jsonify({'progress': progress})


@app.route('/api/stats')
@login_required
def get_stats():
    user_id = request.args.get('user_id', session['user_id'], type=int)
    current = User.query.get(session['user_id'])
    if user_id != session['user_id'] and current.role != 'admin':
        return jsonify({'error': '権限がありません'}), 403

    result = {}
    for mode in ['quick', 'reproduction', 'simulation']:
        answers = (Answer.query
                   .join(Question, Question.id == Answer.question_id)
                   .filter(Answer.user_id == user_id, Question.mode == mode).all())
        if answers:
            best = max(a.score_total for a in answers)
            avg = sum(a.score_total for a in answers) / len(answers)
        else:
            best = avg = None
        result[mode] = {
            'count': len(answers),
            'best_score': best,
            'avg_score': round(avg, 1) if avg else None,
        }
    return jsonify({'stats': result})


@app.route('/api/questions')
@login_required
def get_questions():
    mode = request.args.get('mode', 'quick')
    category_id = request.args.get('category_id', type=int)
    q = Question.query.filter_by(mode=mode, is_active=True)
    if category_id:
        q = q.filter_by(category_id=category_id)
    questions = q.all()

    # Preload templates for context extraction
    template_ids = {q.talk_template_id for q in questions if q.talk_template_id}
    templates = {t.id: t for t in TalkTemplate.query.filter(TalkTemplate.id.in_(template_ids)).all()} if template_ids else {}

    result = []
    for question in questions:
        d = question.to_dict()
        if question.question_type == 'fill_blank':
            # Add phrase reason
            d['phrase_reason'] = PHRASE_REASONS.get(question.customer_text)
            # Add context from script (with answer hidden)
            if question.talk_template_id:
                tmpl = templates.get(question.talk_template_id)
                if tmpl:
                    ctx = extract_context(tmpl.full_script, question.customer_text or '')
                    if ctx and question.correct_answer:
                        ctx = ctx.replace(question.correct_answer, '（　　）')
                    d['context_text'] = ctx
        result.append(d)

    return jsonify({'questions': result})


@app.route('/api/templates/<int:template_id>')
@login_required
def get_template(template_id):
    t = TalkTemplate.query.get_or_404(template_id)
    return jsonify({'template': t.to_dict()})


@app.route('/api/answers', methods=['POST'])
@login_required
def submit_answer():
    data = request.get_json()
    question_id = data.get('question_id')
    answer_text = data.get('answer_text', '').strip()
    question = Question.query.get_or_404(question_id)

    if question.mode in ('reproduction', 'simulation'):
        category = Category.query.get(question.category_id)
        # 複合問題は複数テンプレートを結合
        extra_ids = SIMULATION_MULTI_TEMPLATES.get(question.customer_text or '', [])
        if extra_ids:
            templates_list = TalkTemplate.query.filter(TalkTemplate.id.in_(extra_ids)).order_by(TalkTemplate.id).all()
        else:
            primary = TalkTemplate.query.get(question.talk_template_id)
            templates_list = [primary] if primary else []
        combined_script = '\n\n---\n\n'.join(t.full_script for t in templates_list)
        combined_display = '・'.join(t.display_name for t in templates_list)
        kp = []
        rp = []
        for t in templates_list:
            kp.extend(json.loads(t.key_phrases) if t.key_phrases else [])
            rp.extend(json.loads(t.required_points) if t.required_points else [])
        try:
            result = ai_score(question.mode, category.name, question.customer_text or '',
                              combined_display, combined_script, kp, rp, answer_text)
        except Exception as e:
            return jsonify({'error': f'AI採点エラー: {e}'}), 500
        answer = Answer(user_id=session['user_id'], question_id=question_id,
                        answer_text=answer_text,
                        score_total=result.get('score_total', 0),
                        score_structure=result.get('score_structure', 0),
                        score_reproduction=result.get('score_reproduction', 0),
                        title=result.get('title', '練習スタート'),
                        is_passed=result.get('is_passed', False),
                        has_compliance_ng=result.get('has_compliance_ng', False),
                        compliance_ng_words=json.dumps(result.get('compliance_ng_words', []), ensure_ascii=False),
                        ai_feedback=json.dumps(result, ensure_ascii=False))
    elif question.question_type == 'model_check':
        answer = Answer(user_id=session['user_id'], question_id=question_id,
                        answer_text='(模範トーク確認)', score_total=100,
                        title='シーディングマスター', is_passed=True,
                        ai_feedback=json.dumps({'good_points': ['模範トークを確認しました！'], 'improvement_points': [], 'ideal_answer': ''}, ensure_ascii=False))
    elif question.question_type == 'reorder':
        correct = json.loads(question.correct_answer) if question.correct_answer else []
        user_order = json.loads(answer_text) if answer_text else []
        matches = sum(1 for i, v in enumerate(user_order) if i < len(correct) and v == correct[i])
        score = int(matches / len(correct) * 100) if correct else 0
        answer = Answer(user_id=session['user_id'], question_id=question_id,
                        answer_text=answer_text, score_total=score,
                        title=score_to_title(score), is_passed=(score >= 80),
                        ai_feedback=json.dumps({
                            'good_points': [f'{matches}/{len(correct)} ステップが正解！'] if matches else ['もう一度確認しよう'],
                            'improvement_points': [] if score == 100 else ['正しい順番で覚えましょう'],
                            'ideal_answer': ' → '.join(correct)}, ensure_ascii=False))
    else:
        correct = (question.correct_answer or '').strip()
        ans_l, cor_l = answer_text.lower(), correct.lower()
        if ans_l == cor_l:
            score, is_correct = 100, True
            good = ['正解！完璧です！']
            improve = []
        elif cor_l in ans_l or ans_l in cor_l:
            score, is_correct = 70, False
            good = ['ほぼ正解！ニュアンスはOKです']
            improve = [f'より正確には「{correct}」です']
        else:
            score, is_correct = 0, False
            good = ['惜しい！']
            improve = [f'正解は「{correct}」です']
        answer = Answer(user_id=session['user_id'], question_id=question_id,
                        answer_text=answer_text, score_total=score,
                        title=score_to_title(score), is_passed=is_correct,
                        ai_feedback=json.dumps({
                            'good_points': good,
                            'improvement_points': improve,
                            'ideal_answer': correct}, ensure_ascii=False))

    db.session.add(answer)
    db.session.commit()
    return jsonify({'answer': answer.to_dict(),
                    'feedback': json.loads(answer.ai_feedback) if answer.ai_feedback else None})


@app.route('/api/answers', methods=['GET'])
@login_required
def get_answers():
    current = User.query.get(session['user_id'])
    all_users = request.args.get('all_users') == '1'

    if all_users and current.role == 'admin':
        answers = (Answer.query
                   .order_by(Answer.created_at.desc()).limit(100).all())
    else:
        user_id = request.args.get('user_id', session['user_id'], type=int)
        if user_id != session['user_id'] and current.role != 'admin':
            return jsonify({'error': '権限がありません'}), 403
        answers = Answer.query.filter_by(user_id=user_id).order_by(Answer.created_at.desc()).limit(50).all()

    result = []
    for a in answers:
        d = a.to_dict()
        d['question'] = a.question.to_dict() if a.question else None
        d['category_name'] = (Category.query.get(a.question.category_id).name if a.question else None)
        d['admin_comments'] = [c.to_dict() for c in a.comments]
        d['user_name'] = a.user.name if a.user else None
        result.append(d)
    return jsonify({'answers': result})


@app.route('/api/admin/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.filter_by(role='user').all()
    categories = Category.query.order_by(Category.id).all()
    result = []
    for u in users:
        total = Answer.query.filter_by(user_id=u.id).count()
        # カテゴリ×モード の集計
        cat_stats = {}
        for c in categories:
            modes = {}
            for mode in ['quick', 'reproduction', 'simulation']:
                ans = (Answer.query
                       .join(Question, Question.id == Answer.question_id)
                       .filter(Answer.user_id == u.id,
                               Question.category_id == c.id,
                               Question.mode == mode).all())
                best = max((a.score_total for a in ans), default=None)
                modes[mode] = {'best_score': best, 'count': len(ans)}
            cat_stats[c.id] = {
                'name': c.name, 'emoji': c.emoji, 'modes': modes
            }
        result.append({
            'user': u.to_dict(),
            'total_answers': total,
            'category_stats': cat_stats,
        })
    return jsonify({'members': result})


@app.route('/api/admin/members/<int:uid>')
@admin_required
def member_detail(uid):
    user = User.query.get_or_404(uid)
    answers = Answer.query.filter_by(user_id=uid).order_by(Answer.created_at.desc()).all()
    result = []
    for a in answers:
        d = a.to_dict()
        d['question'] = a.question.to_dict() if a.question else None
        d['category_name'] = (Category.query.get(a.question.category_id).name if a.question else None)
        d['admin_comments'] = [c.to_dict() for c in a.comments]
        result.append(d)
    # Mode stats
    mode_stats = {}
    for mode in ['quick', 'reproduction', 'simulation']:
        ans = (Answer.query.join(Question, Question.id == Answer.question_id)
               .filter(Answer.user_id == uid, Question.mode == mode).all())
        mode_stats[mode] = {
            'count': len(ans),
            'best_score': max((a.score_total for a in ans), default=None),
            'avg_score': round(sum(a.score_total for a in ans) / len(ans), 1) if ans else None,
        }
    return jsonify({'user': user.to_dict(), 'answers': result, 'mode_stats': mode_stats})


@app.route('/api/admin/comments', methods=['POST'])
@admin_required
def add_comment():
    data = request.get_json()
    comment_text = (data.get('comment') or '').strip()
    if not comment_text:
        return jsonify({'error': 'コメントを入力してください'}), 400
    c = AdminComment(answer_id=data.get('answer_id'),
                     admin_user_id=session['user_id'], comment=comment_text)
    db.session.add(c)
    db.session.commit()
    return jsonify({'comment': c.to_dict()})


@app.route('/api/update-day', methods=['POST'])
@login_required
def update_day():
    data = request.get_json()
    day = max(1, min(3, data.get('day', 1)))
    user = User.query.get(session['user_id'])
    user.current_day = day
    db.session.commit()
    return jsonify({'current_day': user.current_day})


# ── Startup ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    seed_db()
    update_templates()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=os.getenv('RAILWAY_ENVIRONMENT') is None, host='0.0.0.0', port=port)
