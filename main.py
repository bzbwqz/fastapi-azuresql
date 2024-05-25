from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional, List
from urllib.parse import quote_plus
from pydantic import BaseModel

app = FastAPI()

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up Azure SQL DB
params = quote_plus("DRIVER={ODBC Driver 17 for SQL Server};"
                    "SERVER={your sql server}.database.windows.net;"
                    "DATABASE={DB Name};"
                    "UID={Username};"
                    "PWD={pw}")

DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"
engine = create_engine(DATABASE_URL, echo=True)

# Dependency to get DB session
def get_db_session():
    with Session(engine) as session:
        yield session

# 更改后的Student类
class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # 假设student表有name和age字段
    name: str
    age: int

class StudentCreate(BaseModel):
    name: str
    age: int

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None

# 检查student表是否存在
def check_table_exists(engine, table_name):
    with engine.connect() as connection:
        return engine.dialect.has_table(connection, table_name)

# 在应用程序启动时执行
@app.on_event("startup")
def on_startup():
    if not check_table_exists(engine, "student"):
        print("Student表不存在，正在创建...")
        SQLModel.metadata.create_all(engine)
    else:
        print("Student表已存在。")

# 更新后的路由，使用Student模型
@app.get("/students/", response_model=List[Student])
def read_students(session: Session = Depends(get_db_session)):
    return session.query(Student).all()

@app.get("/students/{student_id}", response_model=Student)
def read_student(student_id: int, session: Session = Depends(get_db_session)):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.post("/students/", response_model=Student)
def create_student(student: StudentCreate, session: Session = Depends(get_db_session)):
    db_student = Student(name=student.name, age=student.age)
    session.add(db_student)
    session.commit()
    session.refresh(db_student)
    return db_student

@app.patch("/students/{student_id}", response_model=Student)
def update_student(student_id: int, student: StudentUpdate, session: Session = Depends(get_db_session)):
    db_student = session.get(Student, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_data = student.dict(exclude_unset=True)
    for key, value in student_data.items():
        setattr(db_student, key, value)
    session.commit()
    session.refresh(db_student)
    return db_student

@app.delete("/students/{student_id}", response_model=None)
def delete_student(student_id: int, session: Session = Depends(get_db_session)):
    db_student = session.get(Student, student_id)
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    session.delete(db_student)
    session.commit()
    return {"message": "Student记录已被删除"}
