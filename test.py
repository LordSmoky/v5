import tkinter as tk
from tkinter import ttk
from gui_vacation_tab import VacationTab
from db_connection import DatabaseConnection

# Тестовая программа для проверки VacationTab
root = tk.Tk()
root.title("Тест VacationTab")
root.geometry("1000x600")

notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True)

# Создаем подключение к БД
db_conn = DatabaseConnection()

# Создаем вкладку отпусков
vacation_tab = VacationTab(notebook, db_conn)

root.mainloop()