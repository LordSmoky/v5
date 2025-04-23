import tkinter as tk
from gui import SalaryCalculatorGUI
from app import SalaryApp

if __name__ == "__main__":
    # Конфигурация подключения к базе данных
    db_config = {
        'host': 'localhost',
        'database': 'salary_calculator2',
        'user': 'postgres',
        'password': '123321445',
        'port': '5432'
    }
    
    # Создаем корневое окно Tkinter
    root = tk.Tk()
    
    # Инициализируем приложение
    app = SalaryApp(db_config)
    
    # Создаем и запускаем GUI
    gui = SalaryCalculatorGUI(root)
    
    # Запускаем главный цикл событий
    root.mainloop()
    
    # Закрываем приложение при выходе
    app.close()