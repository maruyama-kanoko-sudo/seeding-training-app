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

YAMAKITA_SCRIPT = """相談したいって思うの、すごく大事なことだと思いますし、心配になる気持ちもすごく分かります。

前に山北さんっていう方がいて、旦那さんに最初すごく反対されてたんですよね。

やっぱり"お金大丈夫なの？"とか"時間取れるの？"って、心配から反対されるケースってすごく多くて。

その中で山北さんが言ってたのが、"結局自分の人生だから、自分で決めないと何も変わらない"って。

もしその時にやらなかったら、"あの時やっておけばよかったな"って絶対後悔するし、その時に旦那さんに反対されたからって人のせいにしてしまいそうだったって言ってて。

それが嫌だったから、自分で決断して始められたらしいんです。

最初はやっぱり大変だったみたいなんですけど、結果が出てから旦那さんに初めて認めてもらえて、"あの時やってよかった"って言ってましたね。

なので、相談すること自体は全然いいと思うんですけど、〇〇さんとしては、やりたい気持ちとやりたくない気持ちだったら、どっちが強いですか？"""

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
    kp3 = json.dumps(["結局自分の人生だから、自分で決めないと何も変わらない","人のせいにしてしまいそうだった","やりたい気持ちとやりたくない気持ちだったら、どっちが強いですか"], ensure_ascii=False)
    rp3 = json.dumps(["相談したい気持ちに共感する","山北さんの実例を使う（旦那さんに反対された）","自分で決断することの大切さを伝える","最後はやりたい気持ちを確認する質問で締める"], ensure_ascii=False)
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

def ai_score(mode, category_name, customer_text, talk_display_name, full_script, key_phrases, required_points, answer_text):
    sys_prompt = """あなたは営業トークの採点AIです。
新人営業がプレ即決率を上げるためのシーディングトークを、現場で再現できるようにすることが目的です。

【重要方針】
- 暗記寄りで評価する（模範スクリプトに近いほど高得点）
- 平均営業が70点を取れる基準にする
- 甘すぎず、改善点が分かる評価にする
- フィードバックは新人営業が次に直せる具体的な言葉で出す
- コンプライアンスNGは減点する（1件につき-30点）
- 成果保証・圧迫・断定表現は厳しく評価する
- 実在事例ベースの第三者トークを高く評価する
- 最後は自然な質問で終わっているかを評価する"""

    user_prompt = f"""以下の営業回答を採点してください。

【モード】{mode}
【カテゴリ】{category_name}
【お客様発言】{customer_text}
【指定トーク】{talk_display_name}
【模範スクリプト】
{full_script}
【必須キーフレーズ】{json.dumps(key_phrases, ensure_ascii=False)}
【必須チェック項目】{json.dumps(required_points, ensure_ascii=False)}
【ユーザー回答】
{answer_text}

【採点基準】100点満点
構造評価60点：共感・承認12点、本質の言語化12点、第三者トーク12点、未来提示・行動正当化12点、クロージング設計12点
マストトーク再現度40点：指定トークに合っている8点、話の流れ8点、キーフレーズ8点、具体エピソード8点、最後が質問で終わる8点

コンプライアンスNG（含む場合-30点/件）：絶対稼げます、元取れます、やるべき、やらないと損、強制・圧迫表現、成果保証表現

【出力形式】必ずJSONのみで返してください：
{{"score_total":数値,"is_passed":真偽,"score_structure":数値,"score_reproduction":数値,"has_compliance_ng":真偽,"compliance_ng_words":[],"structure_detail":{{"empathy":数値,"essence":数値,"third_party":数値,"future":数値,"closing":数値}},"reproduction_detail":{{"category_match":数値,"flow":数値,"key_phrases":数値,"episode":数値,"closing_question":数値}},"good_points":["良かった点"],"improvement_points":["改善点"],"missing_key_phrases":["未使用フレーズ"],"safe_rewrite":"","ideal_answer":"理想のトーク例（150字程度）"}}"""

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
    return jsonify({'questions': [x.to_dict() for x in q.all()]})


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
        template = TalkTemplate.query.get(question.talk_template_id)
        category = Category.query.get(question.category_id)
        kp = json.loads(template.key_phrases) if template.key_phrases else []
        rp = json.loads(template.required_points) if template.required_points else []
        try:
            result = ai_score(question.mode, category.name, question.customer_text or '',
                              template.display_name, template.full_script, kp, rp, answer_text)
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
        is_correct = answer_text.lower() == correct.lower()
        score = 100 if is_correct else 0
        answer = Answer(user_id=session['user_id'], question_id=question_id,
                        answer_text=answer_text, score_total=score,
                        title=score_to_title(score), is_passed=is_correct,
                        ai_feedback=json.dumps({
                            'good_points': ['正解！' if is_correct else '惜しい！'],
                            'improvement_points': [] if is_correct else [f'正解は「{correct}」です'],
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=os.getenv('RAILWAY_ENVIRONMENT') is None, host='0.0.0.0', port=port)
