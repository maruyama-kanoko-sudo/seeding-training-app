from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    users = relationship("User", back_populates="team")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    team = relationship("Team", back_populates="users")
    answers = relationship("Answer", back_populates="user")
    feedbacks = relationship("UserFeedback", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    questions = relationship("Question", back_populates="category")
    registered_cases = relationship("RegisteredCase", back_populates="category")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    customer_text = Column(Text, nullable=False)
    expected_points = Column(Text)
    fill_template = Column(Text, nullable=True)
    difficulty = Column(String, default="normal")
    is_active = Column(Boolean, default=True)
    category = relationship("Category", back_populates="questions")
    answers = relationship("Answer", back_populates="question")
    feedbacks = relationship("UserFeedback", back_populates="question")


class RegisteredCase(Base):
    __tablename__ = "registered_cases"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    person_name = Column(String, nullable=False)
    story_text = Column(Text, nullable=False)
    allowed = Column(Boolean, default=True)
    category = relationship("Category", back_populates="registered_cases")


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    compliance_ng = Column(Boolean, default=False)
    ai_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="feedbacks")
    question = relationship("Question", back_populates="feedbacks")
