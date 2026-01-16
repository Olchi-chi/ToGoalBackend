from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import uvicorn

app = FastAPI()

# Настройки CORS
origins = [
    "http://localhost:3000",  
    "http://127.0.0.1:3000"  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных для проектов
class Project(BaseModel):
    id: int = None
    name: str
    description: str
    podrazdelenie: str
    date: str
    skills: Optional[List[int]] = []

# Модель данных для навыков
class Skill(BaseModel):
    id: int = None
    name: str
    description: str

# Модель данных для пользователя
class User(BaseModel):
    id: int = None
    first_name: str
    last_name: str
    password: str

# Модель данных для задач
class Task(BaseModel):
    id: int = None
    project_id: int
    name: str
    description: str
    date: str
    status: str

# Модель данных для формы участия в проекте
class ParticipationForm(BaseModel):
    id: int = None
    user_id: int
    project_id: int
    motivation: str
    experience: str
    availability: str

# Путь к JSON файлам
PROJECTS_DB_FILE = "projects.json"
SKILLS_DB_FILE = "skills.json"
USERS_DB_FILE = "users.json"
TASKS_DB_FILE = "tasks.json"
FORMS_DB_FILE = "forms.json"

# Функция для загрузки данных из JSON файла
def load_data(file_path):
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
            else:
                return []
    except FileNotFoundError:
        return []

# Функция для сохранения данных в JSON файл
def save_data(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

# Маршруты для проектов
@app.get("/projects", response_model=List[Project])
def get_projects():
    projects = load_data(PROJECTS_DB_FILE)
    return projects

@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: int):
    projects = load_data(PROJECTS_DB_FILE)
    for project in projects:
        if project["id"] == project_id:
            return project
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/projects", response_model=Project)
def create_project(project: Project):
    projects = load_data(PROJECTS_DB_FILE)
    new_id = 1 if not projects else max(p["id"] for p in projects) + 1
    new_project = project.dict()
    new_project["id"] = new_id
    projects.append(new_project)
    save_data(PROJECTS_DB_FILE, projects)
    return new_project

@app.put("/projects/{project_id}", response_model=Project)
def update_project(project_id: int, updated_project: Project):
    projects = load_data(PROJECTS_DB_FILE)
    for project in projects:
        if project["id"] == project_id:
            updated_project_dict = updated_project.dict(exclude={"id"})
            project.update(updated_project_dict)
            save_data(PROJECTS_DB_FILE, projects)
            return project
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    projects = load_data(PROJECTS_DB_FILE)
    initial_length = len(projects)
    projects = [p for p in projects if p["id"] != project_id]
    if len(projects) == initial_length:
        raise HTTPException(status_code=404, detail="Project not found")
    save_data(PROJECTS_DB_FILE, projects)
    return {"detail": "Project deleted"}

# Маршруты для навыков
@app.get("/skills", response_model=List[Skill])
def get_skills():
    skills = load_data(SKILLS_DB_FILE)
    return skills

@app.get("/skills/{skill_id}", response_model=Skill)
def get_skill(skill_id: int):
    skills = load_data(SKILLS_DB_FILE)
    for skill in skills:
        if skill["id"] == skill_id:
            return skill
    raise HTTPException(status_code=404, detail="Skill not found")

@app.post("/skills", response_model=Skill)
def create_skill(skill: Skill):
    skills = load_data(SKILLS_DB_FILE)
    new_id = 1 if not skills else max(s["id"] for s in skills) + 1
    new_skill = skill.dict()
    new_skill["id"] = new_id
    skills.append(new_skill)
    save_data(SKILLS_DB_FILE, skills)
    return new_skill

@app.put("/skills/{skill_id}", response_model=Skill)
def update_skill(skill_id: int, updated_skill: Skill):
    skills = load_data(SKILLS_DB_FILE)
    for skill in skills:
        if skill["id"] == skill_id:
            updated_skill_dict = updated_skill.dict(exclude={"id"})
            skill.update(updated_skill_dict)
            save_data(SKILLS_DB_FILE, skills)
            return skill
    raise HTTPException(status_code=404, detail="Skill not found")

@app.delete("/skills/{skill_id}")
def delete_skill(skill_id: int):
    skills = load_data(SKILLS_DB_FILE)
    initial_length = len(skills)
    skills = [s for s in skills if s["id"] != skill_id]
    if len(skills) == initial_length:
        raise HTTPException(status_code=404, detail="Skill not found")
    save_data(SKILLS_DB_FILE, skills)
    return {"detail": "Skill deleted"}

# Маршруты для управления навыками в проектах
@app.post("/projects/{project_id}/skills")
def add_skills_to_project(project_id: int, skill_ids: List[int]):
    projects = load_data(PROJECTS_DB_FILE)
    for project in projects:
        if project["id"] == project_id:
            if "skills" not in project:
                project["skills"] = []
            project["skills"].extend(skill_ids)
            save_data(PROJECTS_DB_FILE, projects)
            return project
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/projects/{project_id}/skills")
def remove_skills_from_project(project_id: int, skill_ids: List[int]):
    projects = load_data(PROJECTS_DB_FILE)
    for project in projects:
        if project["id"] == project_id:
            if "skills" in project:
                project["skills"] = [skill for skill in project["skills"] if skill not in skill_ids]
                save_data(PROJECTS_DB_FILE, projects)
                return project
    raise HTTPException(status_code=404, detail="Project not found")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected.")

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"User {user_id} disconnected.")

    async def send_message(self, sender_id: int, receiver_id: int, message: str):
        if receiver_id in self.active_connections:
            await self.active_connections[receiver_id].send_text(message)
            print(f"Message sent from {sender_id} to {receiver_id}: {message}")

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            receiver_id = message_data["receiver_id"]
            message = message_data["message"]
            await manager.send_message(user_id, receiver_id, message)
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Маршруты для пользователей
@app.post("/register", response_model=User)
def register_user(user: User):
    users = load_data(USERS_DB_FILE)
    new_id = 1 if not users else max(u["id"] for u in users) + 1
    new_user = user.dict()
    new_user["id"] = new_id
    users.append(new_user)
    save_data(USERS_DB_FILE, users)
    return new_user

@app.post("/login", response_model=User)
def login_user(user: User):
    users = load_data(USERS_DB_FILE)
    for u in users:
        if u["first_name"] == user.first_name and u["last_name"] == user.last_name and u["password"] == user.password:
            return u
    raise HTTPException(status_code=400, detail="Incorrect username or password")

# Маршруты для задач
@app.get("/projects/{project_id}/tasks", response_model=List[Task])
def get_tasks(project_id: int):
    tasks = load_data(TASKS_DB_FILE)
    project_tasks = [task for task in tasks if task["project_id"] == project_id]
    return project_tasks

@app.get("/projects/{project_id}/tasks/{task_id}", response_model=Task)
def get_task(project_id: int, task_id: int):
    tasks = load_data(TASKS_DB_FILE)
    for task in tasks:
        if task["id"] == task_id and task["project_id"] == project_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/projects/{project_id}/tasks", response_model=Task)
def create_task(project_id: int, task: Task):
    tasks = load_data(TASKS_DB_FILE)
    new_id = 1 if not tasks else max(t["id"] for t in tasks) + 1
    new_task = task.dict()
    new_task["id"] = new_id
    new_task["project_id"] = project_id
    tasks.append(new_task)
    save_data(TASKS_DB_FILE, tasks)
    return new_task

@app.put("/projects/{project_id}/tasks/{task_id}", response_model=Task)
def update_task(project_id: int, task_id: int, updated_task: Task):
    tasks = load_data(TASKS_DB_FILE)
    for task in tasks:
        if task["id"] == task_id and task["project_id"] == project_id:
            updated_task_dict = updated_task.dict(exclude={"id", "project_id"})
            task.update(updated_task_dict)
            save_data(TASKS_DB_FILE, tasks)
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: int, task_id: int):
    tasks = load_data(TASKS_DB_FILE)
    initial_length = len(tasks)
    tasks = [t for t in tasks if not (t["id"] == task_id and t["project_id"] == project_id)]
    if len(tasks) == initial_length:
        raise HTTPException(status_code=404, detail="Task not found")
    save_data(TASKS_DB_FILE, tasks)
    return {"detail": "Task deleted"}

# Маршруты для формы участия в проекте
@app.get("/forms", response_model=List[ParticipationForm])
def get_forms():
    forms = load_data(FORMS_DB_FILE)
    users = load_data(USERS_DB_FILE)
    # Attach user information to each form
    for form in forms:
        user = next((u for u in users if u["id"] == form["user_id"]), None)
        form["user"] = user
    return forms

@app.get("/forms/{form_id}", response_model=ParticipationForm)
def get_form(form_id: int):
    forms = load_data(FORMS_DB_FILE)
    users = load_data(USERS_DB_FILE)
    for form in forms:
        if form["id"] == form_id:
            user = next((u for u in users if u["id"] == form["user_id"]), None)
            form["user"] = user
            return form
    raise HTTPException(status_code=404, detail="Form not found")

@app.post("/forms", response_model=ParticipationForm)
def create_form(form: ParticipationForm):
    forms = load_data(FORMS_DB_FILE)
    # Check if a form with the same user_id and project_id already exists
    for existing_form in forms:
        if existing_form["user_id"] == form.user_id and existing_form["project_id"] == form.project_id:
            raise HTTPException(status_code=400, detail="Form already submitted for this project")
    new_id = 1 if not forms else max(f["id"] for f in forms) + 1
    new_form = form.dict()
    new_form["id"] = new_id
    forms.append(new_form)
    save_data(FORMS_DB_FILE, forms)
    return new_form

@app.put("/forms/{form_id}", response_model=ParticipationForm)
def update_form(form_id: int, updated_form: ParticipationForm):
    forms = load_data(FORMS_DB_FILE)
    for form in forms:
        if form["id"] == form_id:
            updated_form_dict = updated_form.dict(exclude={"id"})
            form.update(updated_form_dict)
            save_data(FORMS_DB_FILE, forms)
            return form
    raise HTTPException(status_code=404, detail="Form not found")

@app.delete("/forms/{form_id}")
def delete_form(form_id: int):
    forms = load_data(FORMS_DB_FILE)
    initial_length = len(forms)
    forms = [f for f in forms if f["id"] != form_id]
    if len(forms) == initial_length:
        raise HTTPException(status_code=404, detail="Form not found")
    save_data(FORMS_DB_FILE, forms)
    return {"detail": "Form deleted"}

# Добавление WebSocket в OpenAPI документацию
@app.on_event("startup")
async def startup_event():
    openapi_schema = app.openapi()
    openapi_schema["components"]["schemas"]["WebSocketMessage"] = {
        "type": "object",
        "properties": {
            "receiver_id": {"type": "integer"},
            "message": {"type": "string"},
        },
        "required": ["receiver_id", "message"],
    }
    openapi_schema["paths"]["/ws/{user_id}"] = {
        "get": {
            "summary": "WebSocket Endpoint",
            "description": "WebSocket endpoint for chat between users.",
            "operationId": "websocket_endpoint",
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                    "description": "The ID of the user",
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/WebSocketMessage"}
                        }
                    },
                }
            },
        }
    }
    app.openapi_schema = openapi_schema

# Запуск сервера
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8470)
