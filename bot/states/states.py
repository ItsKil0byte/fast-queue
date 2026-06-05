from aiogram.fsm.state import State, StatesGroup
 
 
class StudentSG(StatesGroup):
    idle = State()
    entering_queue_id = State()   # студент вводит ID очереди
    choosing_lab = State()
    in_queue = State()
    at_defense = State()
 
 
class TeacherSG(StatesGroup):
    idle = State()
    creating_queue = State()
    creating_queue_classroom = State()
    managing = State()
 