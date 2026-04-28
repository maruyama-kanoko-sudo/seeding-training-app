import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
from ai_scorer import score_answer

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-32chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

app = FastAPI(title="シーディングトレーニングアプリ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 起動時にDBテーブル作成＆初期データ投入
@app.on_event("startup")
async def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ DBテーブル作成完了")
    except Exception as e:
        print(f"⚠️ DBテーブル作成エラー: {e}")
    try:
        from init_db import init
        init()
        print("✅ 初期データ投入完了")
    except Exception as e:
        print(f"DB初期化スキップ（既に初期化済み）: {e}")


# ---------- Pydantic schemas ----------

class LoginRequest(BaseModel):
    email: str
    password: str

class AnswerSubmit(BaseModel):
    question_id: int
    answer_text: str

class FeedbackSubmit(BaseModel):
    question_id: int
    message: str

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class QuestionCreate(BaseModel):
    category_id: int
    customer_text: str
    expected_points: Optional[str] = None
    difficulty: str = "normal"

class QuestionUpdate(BaseModel):
    customer_text: Optional[str] = None
    expected_points: Optional[str] = None
    difficulty: Optional[str] = None
    is_active: Optional[bool] = None

class CaseCreate(BaseModel):
    category_id: int
    person_name: str
    story_text: str
    allowed: bool = True

class CaseUpdate(BaseModel):
    person_name: Optional[str] = None
    story_text: Optional[str] = None
    allowed: Optional[bool] = None

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"
    team_id: Optional[int] = None


# ---------- Auth helpers ----------

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def _get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="認証情報が無効です")
    except JWTError:
        raise HTTPException(status_code=401, detail="認証情報が無効です")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
    return user

def require_auth(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証が必要です")
    return _get_user_from_token(authorization[7:], db)

def require_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証が必要です")
    user = _get_user_from_token(authorization[7:], db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return user


# ---------- Auth routes ----------

@app.post("/api/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが間違っています")
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "team_id": user.team_id,
            "team_name": user.team.name if user.team else None,
        },
    }

@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(require_auth)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "team_id": current_user.team_id,
        "team_name": current_user.team.name if current_user.team else None,
    }


# ---------- Category / Question routes ----------

@app.get("/api/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    categories = db.query(models.Category).all()
    result = []
    for cat in categories:
        qcount = db.query(models.Question).filter(
            models.Question.category_id == cat.id,
            models.Question.is_active == True,
        ).count()
        result.append({"id": cat.id, "name": cat.name, "description": cat.description, "question_count": qcount})
    return result

@app.get("/api/questions/{category_id}/random")
def get_random_question(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    questions = db.query(models.Question).filter(
        models.Question.category_id == category_id,
        models.Question.is_active == True,
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="この カテゴリに有効な問題がありません")
    q = random.choice(questions)
    return {
        "id": q.id,
        "category_id": q.category_id,
        "category_name": q.category.name,
        "customer_text": q.customer_text,
        "expected_points": q.expected_points,
        "fill_template": q.fill_template,
        "difficulty": q.difficulty,
    }


# ---------- Answer routes ----------

@app.post("/api/answers")
def submit_answer(
    request: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    question = db.query(models.Question).filter(models.Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="問題が見つかりません")

    cases = db.query(models.RegisteredCase).filter(
        models.RegisteredCase.allowed == True,
    ).all()
    cases_data = [{"person_name": c.person_name, "story_text": c.story_text, "allowed": c.allowed} for c in cases]

    try:
        ai_result = score_answer(
            category_name=question.category.name,
            customer_text=question.customer_text,
            answer_text=request.answer_text,
            registered_cases=cases_data,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI採点エラー: {str(e)}")

    answer = models.Answer(
        user_id=current_user.id,
        question_id=request.question_id,
        answer_text=request.answer_text,
        score=ai_result["score"],
        passed=ai_result["passed"],
        compliance_ng=ai_result["compliance_ng"],
        ai_feedback=json.dumps(ai_result, ensure_ascii=False),
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return {
        "answer_id": answer.id,
        "score": ai_result["score"],
        "passed": ai_result["passed"],
        "compliance_ng": ai_result["compliance_ng"],
        "compliance_reasons": ai_result.get("compliance_reasons", []),
        "details": ai_result["details"],
        "good_points": ai_result.get("good_points", ""),
        "improvement_points": ai_result.get("improvement_points", ""),
        "suggested_answer": ai_result.get("suggested_answer", ""),
        "category_name": question.category.name,
        "customer_text": question.customer_text,
        "answer_text": request.answer_text,
    }

@app.get("/api/answers/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    answers = (
        db.query(models.Answer)
        .filter(models.Answer.user_id == current_user.id)
        .order_by(models.Answer.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for a in answers:
        feedback = json.loads(a.ai_feedback) if a.ai_feedback else {}
        result.append({
            "id": a.id,
            "question_id": a.question_id,
            "category_name": a.question.category.name if a.question else "不明",
            "customer_text": a.question.customer_text if a.question else "",
            "answer_text": a.answer_text,
            "score": a.score,
            "passed": a.passed,
            "compliance_ng": a.compliance_ng,
            "details": feedback.get("details", {}),
            "good_points": feedback.get("good_points", ""),
            "improvement_points": feedback.get("improvement_points", ""),
            "suggested_answer": feedback.get("suggested_answer", ""),
            "created_at": a.created_at.isoformat(),
        })
    return result

@app.post("/api/feedback")
def submit_feedback(
    request: FeedbackSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_auth),
):
    fb = models.UserFeedback(
        user_id=current_user.id,
        question_id=request.question_id,
        message=request.message,
    )
    db.add(fb)
    db.commit()
    return {"message": "フィードバックを送信しました"}


# ---------- Admin routes ----------

@app.get("/api/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    all_answers = db.query(models.Answer).all()
    total = len(all_answers)
    passed = sum(1 for a in all_answers if a.passed)
    ng_count = sum(1 for a in all_answers if a.compliance_ng)
    scores = [a.score for a in all_answers if a.score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    pass_rate = round(passed / total * 100, 1) if total else 0

    recent = []
    for a in sorted(all_answers, key=lambda x: x.created_at, reverse=True)[:10]:
        recent.append({
            "id": a.id,
            "user_name": a.user.name if a.user else "不明",
            "category_name": a.question.category.name if a.question else "不明",
            "score": a.score,
            "passed": a.passed,
            "compliance_ng": a.compliance_ng,
            "created_at": a.created_at.isoformat(),
        })

    return {
        "total_answers": total,
        "avg_score": avg_score,
        "pass_rate": pass_rate,
        "ng_count": ng_count,
        "recent_answers": recent,
    }

@app.get("/api/admin/users")
def admin_get_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    users = db.query(models.User).filter(models.User.role == "user").all()
    result = []
    for u in users:
        answers = u.answers
        scores = [a.score for a in answers if a.score is not None]
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "team_name": u.team.name if u.team else "未所属",
            "total_answers": len(answers),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "passed_count": sum(1 for a in answers if a.passed),
            "failed_count": sum(1 for a in answers if not a.passed),
            "created_at": u.created_at.isoformat(),
        })
    return result

@app.post("/api/admin/users")
def admin_create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    if db.query(models.User).filter(models.User.email == request.email).first():
        raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")
    user = models.User(
        name=request.name,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=request.role,
        team_id=request.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

@app.get("/api/admin/users/{user_id}")
def admin_get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    answers = (
        db.query(models.Answer)
        .filter(models.Answer.user_id == user_id)
        .order_by(models.Answer.created_at.desc())
        .all()
    )
    scores = [a.score for a in answers if a.score is not None]
    answer_list = []
    for a in answers:
        feedback = json.loads(a.ai_feedback) if a.ai_feedback else {}
        answer_list.append({
            "id": a.id,
            "category_name": a.question.category.name if a.question else "不明",
            "customer_text": a.question.customer_text if a.question else "",
            "answer_text": a.answer_text,
            "score": a.score,
            "passed": a.passed,
            "compliance_ng": a.compliance_ng,
            "good_points": feedback.get("good_points", ""),
            "improvement_points": feedback.get("improvement_points", ""),
            "created_at": a.created_at.isoformat(),
        })
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "team_name": user.team.name if user.team else "未所属",
        "total_answers": len(answers),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "passed_count": sum(1 for a in answers if a.passed),
        "failed_count": sum(1 for a in answers if not a.passed),
        "answers": answer_list,
    }

@app.get("/api/admin/rankings")
def admin_rankings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    teams = db.query(models.Team).all()
    result = []
    for team in teams:
        users = db.query(models.User).filter(models.User.team_id == team.id).all()
        all_answers = [a for u in users for a in u.answers]
        scores = [a.score for a in all_answers if a.score is not None]
        result.append({
            "team_id": team.id,
            "team_name": team.name,
            "member_count": len(users),
            "total_answers": len(all_answers),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "pass_rate": round(sum(1 for a in all_answers if a.passed) / len(all_answers) * 100, 1) if all_answers else 0,
        })
    result.sort(key=lambda x: x["avg_score"], reverse=True)
    for i, r in enumerate(result):
        r["rank"] = i + 1
    return result

@app.get("/api/admin/feedback")
def admin_get_feedback(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    feedbacks = db.query(models.UserFeedback).order_by(models.UserFeedback.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "user_name": f.user.name if f.user else "不明",
            "category_name": f.question.category.name if f.question and f.question.category else "不明",
            "customer_text": f.question.customer_text if f.question else "",
            "message": f.message,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]

@app.get("/api/admin/categories")
def admin_get_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    cats = db.query(models.Category).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in cats]

@app.post("/api/admin/categories")
def admin_create_category(
    request: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    cat = models.Category(name=request.name, description=request.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "description": cat.description}

@app.get("/api/admin/questions")
def admin_get_questions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    questions = db.query(models.Question).all()
    return [
        {
            "id": q.id,
            "category_id": q.category_id,
            "category_name": q.category.name,
            "customer_text": q.customer_text,
            "expected_points": q.expected_points,
            "difficulty": q.difficulty,
            "is_active": q.is_active,
        }
        for q in questions
    ]

@app.post("/api/admin/questions")
def admin_create_question(
    request: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    q = models.Question(
        category_id=request.category_id,
        customer_text=request.customer_text,
        expected_points=request.expected_points,
        difficulty=request.difficulty,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "category_id": q.category_id, "customer_text": q.customer_text}

@app.put("/api/admin/questions/{question_id}")
def admin_update_question(
    question_id: int,
    request: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="問題が見つかりません")
    if request.customer_text is not None:
        q.customer_text = request.customer_text
    if request.expected_points is not None:
        q.expected_points = request.expected_points
    if request.difficulty is not None:
        q.difficulty = request.difficulty
    if request.is_active is not None:
        q.is_active = request.is_active
    db.commit()
    return {"id": q.id, "is_active": q.is_active}

@app.get("/api/admin/cases")
def admin_get_cases(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    cases = db.query(models.RegisteredCase).all()
    return [
        {
            "id": c.id,
            "category_id": c.category_id,
            "category_name": c.category.name,
            "person_name": c.person_name,
            "story_text": c.story_text,
            "allowed": c.allowed,
        }
        for c in cases
    ]

@app.post("/api/admin/cases")
def admin_create_case(
    request: CaseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    case = models.RegisteredCase(
        category_id=request.category_id,
        person_name=request.person_name,
        story_text=request.story_text,
        allowed=request.allowed,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "person_name": case.person_name}

@app.put("/api/admin/cases/{case_id}")
def admin_update_case(
    case_id: int,
    request: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    case = db.query(models.RegisteredCase).filter(models.RegisteredCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="事例が見つかりません")
    if request.person_name is not None:
        case.person_name = request.person_name
    if request.story_text is not None:
        case.story_text = request.story_text
    if request.allowed is not None:
        case.allowed = request.allowed
    db.commit()
    return {"id": case.id, "allowed": case.allowed}

@app.get("/api/admin/teams")
def admin_get_teams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    teams = db.query(models.Team).all()
    return [{"id": t.id, "name": t.name} for t in teams]


# ---------- Static files & SPA ----------

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    return FileResponse("static/index.html")
