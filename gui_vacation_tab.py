import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import calendar
from tkcalendar import DateEntry
from typing import Dict, Any, List, Optional, Callable
import logging

from vacation_processor import VacationProcessor
from db_connection import DatabaseConnection, TeacherRepository

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VacationTab:
    """Класс для реализации интерфейса вкладки отпусков"""
    
    def __init__(self, parent_notebook, db_conn: DatabaseConnection):
        """
        Инициализация вкладки отпусков
        
        :param parent_notebook: родительский объект notebook
        :param db_conn: объект подключения к базе данных
        """
        self.db_conn = db_conn
        self.vacation_processor = VacationProcessor(db_conn)
        
        # Создаем вкладку
        self.tab = ttk.Frame(parent_notebook)
        parent_notebook.add(self.tab, text="Отпуска")
        
        # Создаем интерфейс вкладки
        self._create_ui()
        
        # Загружаем список преподавателей
        self._load_teachers()
        
        # Текущий выбранный преподаватель
        self.current_teacher_id = None
        
    def _create_ui(self):
        """Создание пользовательского интерфейса вкладки"""
        # Основной контейнер с двумя панелями
        self.main_paned = ttk.PanedWindow(self.tab, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель - выбор преподавателя и добавление отпуска
        self.left_frame = ttk.LabelFrame(self.main_paned, text="Данные преподавателя")
        self.main_paned.add(self.left_frame, weight=1)
        
        # Правая панель - список отпусков и действия с ними
        self.right_frame = ttk.LabelFrame(self.main_paned, text="Отпуска")
        self.main_paned.add(self.right_frame, weight=2)
        
        # Наполняем левую панель
        self._create_left_panel()
        
        # Наполняем правую панель
        self._create_right_panel()
    
    def _create_left_panel(self):
        """Создание левой панели с выбором преподавателя и добавлением отпуска"""
        # Фрейм выбора преподавателя
        select_teacher_frame = ttk.Frame(self.left_frame)
        select_teacher_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(select_teacher_frame, text="Выберите преподавателя:").pack(anchor=tk.W)
        
        # Выпадающий список преподавателей
        self.teacher_var = tk.StringVar()
        self.teacher_combobox = ttk.Combobox(select_teacher_frame, textvariable=self.teacher_var, state="readonly")
        self.teacher_combobox.pack(fill=tk.X, pady=2)
        self.teacher_combobox.bind("<<ComboboxSelected>>", self._on_teacher_selected)
        
        # Фрейм с информацией о преподавателе
        teacher_info_frame = ttk.LabelFrame(self.left_frame, text="Информация")
        teacher_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Данные преподавателя
        ttk.Label(teacher_info_frame, text="Должность:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.position_label = ttk.Label(teacher_info_frame, text="-")
        self.position_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Стаж:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.experience_label = ttk.Label(teacher_info_frame, text="-")
        self.experience_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Положено дней:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_days_label = ttk.Label(teacher_info_frame, text="-")
        self.total_days_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Использовано:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.used_days_label = ttk.Label(teacher_info_frame, text="-")
        self.used_days_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Перенесено на год:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.transferred_in_label = ttk.Label(teacher_info_frame, text="-")
        self.transferred_in_label.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Перенесено с года:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.transferred_out_label = ttk.Label(teacher_info_frame, text="-")
        self.transferred_out_label.grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(teacher_info_frame, text="Осталось:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        self.remaining_days_label = ttk.Label(teacher_info_frame, text="-")
        self.remaining_days_label.grid(row=6, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Фрейм добавления нового отпуска
        add_vacation_frame = ttk.LabelFrame(self.left_frame, text="Добавить отпуск")
        add_vacation_frame.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        
        ttk.Label(add_vacation_frame, text="Тип отпуска:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.vacation_type_var = tk.StringVar(value="основной")
        vacation_types = ["основной", "учебный", "без содержания"]
        self.vacation_type_combobox = ttk.Combobox(add_vacation_frame, textvariable=self.vacation_type_var, 
                                                 values=vacation_types, state="readonly")
        self.vacation_type_combobox.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        # Поля выбора дат
        ttk.Label(add_vacation_frame, text="Дата начала:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.start_date_entry = DateEntry(add_vacation_frame, width=12, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        self.start_date_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.start_date_entry.bind("<<DateEntrySelected>>", self._calculate_days)
        
        ttk.Label(add_vacation_frame, text="Дата окончания:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.end_date_entry = DateEntry(add_vacation_frame, width=12, background='darkblue',
                                       foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        self.end_date_entry.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.end_date_entry.bind("<<DateEntrySelected>>", self._calculate_days)
        
        ttk.Label(add_vacation_frame, text="Количество дней:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.days_count_var = tk.StringVar(value="0")
        self.days_count_label = ttk.Label(add_vacation_frame, textvariable=self.days_count_var)
        self.days_count_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(add_vacation_frame, text="Примечания:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.notes_text = tk.Text(add_vacation_frame, height=4, width=20)
        self.notes_text.grid(row=4, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        # Кнопки действий
        button_frame = ttk.Frame(add_vacation_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.add_button = ttk.Button(button_frame, text="Добавить отпуск", command=self._add_vacation)
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Очистить", command=self._clear_vacation_form)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Добавляем отступы для всех виджетов в add_vacation_frame
        for child in add_vacation_frame.winfo_children():
            child.grid_configure(padx=5, pady=3)
        
        # Растягиваем колонки
        add_vacation_frame.grid_columnconfigure(1, weight=1)
        
        # Обновляем количество дней по умолчанию
        self._calculate_days(None)
        
        # Кнопка для переноса дней отпуска
        self.transfer_button = ttk.Button(self.left_frame, text="Перенести дни отпуска", command=self._show_transfer_dialog)
        self.transfer_button.pack(pady=10)
    
    def _create_right_panel(self):
        """Создание правой панели со списком отпусков и деталями"""
        # Фильтры отпусков
        filter_frame = ttk.Frame(self.right_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Год:").pack(side=tk.LEFT, padx=5)
        current_year = datetime.date.today().year
        years = [str(year) for year in range(current_year - 5, current_year + 2)]
        self.year_var = tk.StringVar(value=str(current_year))
        self.year_combobox = ttk.Combobox(filter_frame, textvariable=self.year_var, 
                                         values=years, state="readonly", width=8)
        self.year_combobox.pack(side=tk.LEFT, padx=5)
        self.year_combobox.bind("<<ComboboxSelected>>", lambda e: self._load_vacations())
        
        self.show_cancelled_var = tk.BooleanVar(value=False)
        self.show_cancelled_check = ttk.Checkbutton(filter_frame, text="Показать отмененные", 
                                                variable=self.show_cancelled_var, 
                                                command=self._load_vacations)
        self.show_cancelled_check.pack(side=tk.LEFT, padx=10)
        
        self.btn_all_vacations = ttk.Button(filter_frame, text="Все преподаватели", 
                                          command=self._show_all_vacations)
        self.btn_all_vacations.pack(side=tk.RIGHT, padx=5)
        
        self.btn_refresh = ttk.Button(filter_frame, text="Обновить", 
                                    command=self._load_vacations)
        self.btn_refresh.pack(side=tk.RIGHT, padx=5)
        
        # Таблица отпусков
        table_frame = ttk.Frame(self.right_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем таблицу (Treeview)
        columns = ("id", "teacher", "start_date", "end_date", "days_count", "vacation_type", "status", "payment")
        self.vacations_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Определяем заголовки столбцов
        self.vacations_tree.heading("id", text="ID")
        self.vacations_tree.heading("teacher", text="Преподаватель")
        self.vacations_tree.heading("start_date", text="Начало")
        self.vacations_tree.heading("end_date", text="Окончание")
        self.vacations_tree.heading("days_count", text="Дней")
        self.vacations_tree.heading("vacation_type", text="Тип")
        self.vacations_tree.heading("status", text="Статус")
        self.vacations_tree.heading("payment", text="Сумма")
        
        # Настраиваем ширину столбцов
        self.vacations_tree.column("id", width=50, anchor=tk.CENTER)
        self.vacations_tree.column("teacher", width=120, anchor=tk.W)
        self.vacations_tree.column("start_date", width=80, anchor=tk.CENTER)
        self.vacations_tree.column("end_date", width=80, anchor=tk.CENTER)
        self.vacations_tree.column("days_count", width=50, anchor=tk.CENTER)
        self.vacations_tree.column("vacation_type", width=100, anchor=tk.W)
        self.vacations_tree.column("status", width=100, anchor=tk.W)
        self.vacations_tree.column("payment", width=80, anchor=tk.E)
        
        # Добавляем таблицу и полосу прокрутки на фрейм
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.vacations_tree.yview)
        self.vacations_tree.configure(yscrollcommand=scrollbar.set)
        
        self.vacations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязываем двойной клик для просмотра деталей
        self.vacations_tree.bind("<Double-1>", self._show_vacation_details)
        
        # Фрейм с кнопками действий над отпусками
        actions_frame = ttk.Frame(self.right_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_cancel = ttk.Button(actions_frame, text="Отменить отпуск", 
                                   command=self._cancel_vacation)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.btn_mark_used = ttk.Button(actions_frame, text="Отметить как использованный", 
                                       command=self._mark_vacation_as_used)
        self.btn_mark_used.pack(side=tk.LEFT, padx=5)
        
        self.btn_calculate_payment = ttk.Button(actions_frame, text="Рассчитать выплату", 
                                              command=self._calculate_vacation_payment)
        self.btn_calculate_payment.pack(side=tk.LEFT, padx=5)
        
        # Дополнительные кнопки для отчетов и статистики
        reports_frame = ttk.Frame(self.right_frame)
        reports_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_vacation_stats = ttk.Button(reports_frame, text="Статистика", 
                                           command=self._show_vacation_statistics)
        self.btn_vacation_stats.pack(side=tk.LEFT, padx=5)
        
        self.btn_export_report = ttk.Button(reports_frame, text="Экспорт отчета", 
                                          command=self._export_vacation_report)
        self.btn_export_report.pack(side=tk.LEFT, padx=5)
    
    def _load_teachers(self):
        """Загрузка списка преподавателей в выпадающий список"""
        try:
            teacher_repo = self.db_conn.get_repository('teacher')
            teachers = teacher_repo.get_all_teachers()
            
            self.teachers_data = {}
            self.teacher_names = []
            
            for teacher in teachers:
                teacher_id = teacher['id']
                teacher_name = teacher['name']
                self.teachers_data[teacher_name] = teacher
                self.teacher_names.append(teacher_name)
            
            self.teacher_combobox['values'] = self.teacher_names
            
            if self.teacher_names:
                self.teacher_combobox.current(0)
                self._on_teacher_selected(None)
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка преподавателей: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить список преподавателей: {str(e)}")
    
    def _on_teacher_selected(self, event):
        """Обработчик выбора преподавателя из списка"""
        selected_teacher_name = self.teacher_var.get()
        if not selected_teacher_name:
            return
        
        teacher = self.teachers_data.get(selected_teacher_name)
        if not teacher:
            return
        
        self.current_teacher_id = teacher['id']
        
        self.position_label.config(text=teacher.get('position', "-"))
        self.experience_label.config(text=f"{teacher.get('experience_years', 0)} лет")
        
        try:
            current_year = datetime.date.today().year
            year_from_combobox = int(self.year_var.get()) if self.year_var.get() else current_year
            
            total_days = self.vacation_processor.get_teacher_vacation_days(teacher['id'])
            used_days = self.vacation_processor.get_teacher_used_vacation_days(teacher['id'], year_from_combobox)
            transferred_in = self.vacation_processor.get_transferred_vacation_days_in(teacher['id'], year_from_combobox)
            transferred_out = self.vacation_processor.get_transferred_vacation_days_out(teacher['id'], year_from_combobox)
            remaining_days = self.vacation_processor.get_teacher_remaining_vacation_days(teacher['id'], year_from_combobox)
            
            self.total_days_label.config(text=str(total_days))
            self.used_days_label.config(text=str(used_days))
            self.transferred_in_label.config(text=str(transferred_in))
            self.transferred_out_label.config(text=str(transferred_out))
            self.remaining_days_label.config(text=str(remaining_days))
            
            self._load_vacations()
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о преподавателе: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось получить данные об отпусках: {str(e)}")
    
    def _calculate_days(self, event):
        """Расчет количества дней отпуска между выбранными датами"""
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            
            if start_date and end_date:
                days_count = (end_date - start_date).days + 1
                if days_count < 1:
                    self.days_count_var.set("0")
                else:
                    self.days_count_var.set(str(days_count))
        except Exception as e:
            logger.error(f"Ошибка при расчете количества дней отпуска: {str(e)}")
            self.days_count_var.set("Ошибка")
    
    def _load_vacations(self):
        """Загрузка списка отпусков для выбранного преподавателя"""
        for item in self.vacations_tree.get_children():
            self.vacations_tree.delete(item)
        
        if not self.current_teacher_id:
            return
        
        try:
            year = int(self.year_var.get()) if self.year_var.get() else None
            include_cancelled = self.show_cancelled_var.get()
            
            vacations = self.vacation_processor.get_teacher_vacations(
                self.current_teacher_id, year, include_cancelled)
            
            for vacation in vacations:
                start_date = vacation['start_date'].strftime('%d.%m.%Y')
                end_date = vacation['end_date'].strftime('%d.%m.%Y')
                payment_amount = f"{vacation['payment_amount']:.2f}" if vacation['payment_amount'] else "-"
                
                self.vacations_tree.insert("", tk.END, values=(
                    vacation['id'],
                    vacation['teacher_name'],
                    start_date,
                    end_date,
                    vacation['days_count'],
                    vacation['vacation_type'],
                    vacation['status'],
                    payment_amount
                ))
        except Exception as e:
            logger.error(f"Ошибка при загрузке отпусков: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить отпуска: {str(e)}")
    
    def _show_all_vacations(self):
        """Показать отпуска всех преподавателей"""
        for item in self.vacations_tree.get_children():
            self.vacations_tree.delete(item)
        
        try:
            vacations = self.vacation_processor.get_all_current_vacations(include_past_days=30)
            
            for vacation in vacations:
                start_date = vacation['start_date'].strftime('%d.%m.%Y')
                end_date = vacation['end_date'].strftime('%d.%m.%Y')
                payment_amount = f"{vacation['payment_amount']:.2f}" if vacation['payment_amount'] else "-"
                
                self.vacations_tree.insert("", tk.END, values=(
                    vacation['id'],
                    vacation['teacher_name'],
                    start_date,
                    end_date,
                    vacation['days_count'],
                    vacation['vacation_type'],
                    vacation['status'],
                    payment_amount
                ), tags=('all_vacations',))
        except Exception as e:
            logger.error(f"Ошибка при загрузке всех отпусков: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить все отпуска: {str(e)}")
    
    def _add_vacation(self):
        """Добавление нового отпуска"""
        if not self.current_teacher_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите преподавателя")
            return
        
        try:
            start_date = self.start_date_entry.get_date()
            end_date = self.end_date_entry.get_date()
            vacation_type = self.vacation_type_var.get()
            notes = self.notes_text.get("1.0", tk.END).strip()
            
            if start_date > end_date:
                messagebox.showerror("Ошибка", "Дата начала не может быть позже даты окончания")
                return
            
            vacation_id = self.vacation_processor.schedule_vacation(
                self.current_teacher_id, start_date, end_date, vacation_type, notes)
            
            messagebox.showinfo("Успех", f"Отпуск успешно запланирован (ID: {vacation_id})")
            
            self._on_teacher_selected(None)
            self._clear_vacation_form()
        except Exception as e:
            logger.error(f"Ошибка при добавлении отпуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось добавить отпуск: {str(e)}")
    
    def _clear_vacation_form(self):
        """Очистка формы добавления отпуска"""
        today = datetime.date.today()
        self.start_date_entry.set_date(today)
        self.end_date_entry.set_date(today)
        self.notes_text.delete("1.0", tk.END)
        self.vacation_type_var.set("основной")
        self._calculate_days(None)
    
    def _get_selected_vacation_id(self):
        """Получение ID выбранного отпуска"""
        selection = self.vacations_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Сначала выберите отпуск из списка")
            return None
        
        item = self.vacations_tree.item(selection[0])
        vacation_id = item['values'][0]
        return vacation_id
    
    def _cancel_vacation(self):
        """Отмена выбранного отпуска"""
        vacation_id = self._get_selected_vacation_id()
        if not vacation_id:
            return
        
        try:
            if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите отменить выбранный отпуск?"):
                return
            
            result = self.vacation_processor.cancel_vacation(vacation_id)
            
            if result:
                messagebox.showinfo("Успех", "Отпуск успешно отменен")
                self._load_vacations()
            else:
                messagebox.showwarning("Предупреждение", "Не удалось отменить отпуск. Возможно, его статус не позволяет отмену.")
        except Exception as e:
            logger.error(f"Ошибка при отмене отпуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось отменить отпуск: {str(e)}")
    
    def _mark_vacation_as_used(self):
        """Отметка выбранного отпуска как использованного"""
        vacation_id = self._get_selected_vacation_id()
        if not vacation_id:
            return
        
        try:
            if not messagebox.askyesno("Подтверждение", "Отметить выбранный отпуск как использованный?"):
                return
            
            result = self.vacation_processor.mark_vacation_as_used(vacation_id)
            
            if result:
                messagebox.showinfo("Успех", "Отпуск успешно отмечен как использованный")
                self._load_vacations()
            else:
                messagebox.showwarning("Предупреждение", 
                                    "Не удалось изменить статус отпуска. Возможно, его текущий статус не позволяет изменение.")
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса отпуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось изменить статус отпуска: {str(e)}")
    
    def _calculate_vacation_payment(self):
        """Расчет выплаты за отпуск"""
        vacation_id = self._get_selected_vacation_id()
        if not vacation_id:
            return
        
        try:
            if not messagebox.askyesno("Подтверждение", "Выполнить расчет выплаты за отпуск?"):
                return
            
            payment_info = self.vacation_processor.calculate_vacation_payment(vacation_id)
            
            message = (
                f"Расчет выплаты за отпуск выполнен успешно:\n\n"
                f"Преподаватель: {payment_info['teacher_name']}\n"
                f"Период: {payment_info['start_date'].strftime('%d.%m.%Y')} - {payment_info['end_date'].strftime('%d.%m.%Y')}\n"
                f"Количество дней: {payment_info['vacation_days']}\n"
                f"Средняя дневная зарплата: {payment_info['avg_daily_salary']:.2f}\n\n"
                f"Сумма отпускных (брутто): {payment_info['gross_vacation_pay']:.2f}\n"
                f"Сумма налога: {payment_info['tax_amount']:.2f}\n"
                f"Профсоюзные взносы: {payment_info['union_contribution']:.2f}\n"
                f"Сумма к выплате (нетто): {payment_info['net_vacation_pay']:.2f}"
            )
            
            messagebox.showinfo("Расчет отпускных", message)
            self._load_vacations()
        except Exception as e:
            logger.error(f"Ошибка при расчете отпускных: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось рассчитать отпускные: {str(e)}")
    
    def _show_vacation_details(self, event):
        """Показать детали выбранного отпуска"""
        vacation_id = self._get_selected_vacation_id()
        if not vacation_id:
            return
        
        try:
            vacation = self.vacation_processor.get_vacation_by_id(vacation_id)
            
            if not vacation:
                messagebox.showwarning("Предупреждение", "Отпуск не найден")
                return
            
            details_window = tk.Toplevel()
            details_window.title(f"Отпуск #{vacation_id}")
            details_window.geometry("500x450")
            details_window.resizable(False, False)
            details_window.grab_set()
            
            details_window.update_idletasks()
            width = details_window.winfo_width()
            height = details_window.winfo_height()
            x = (details_window.winfo_screenwidth() // 2) - (width // 2)
            y = (details_window.winfo_screenheight() // 2) - (height // 2)
            details_window.geometry(f"+{x}+{y}")
            
            main_frame = ttk.Frame(details_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="Информация об отпуске", font=("Arial", 12, "bold")).grid(
                row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
            
            row = 1
            for label_text, value in [
                ("ID отпуска:", vacation['id']),
                ("Преподаватель:", vacation['teacher_name']),
                ("Дата начала:", vacation['start_date'].strftime('%d.%m.%Y')),
                ("Дата окончания:", vacation['end_date'].strftime('%d.%m.%Y')),
                ("Количество дней:", vacation['days_count']),
                ("Тип отпуска:", vacation['vacation_type']),
                ("Статус:", vacation['status']),
                ("Сумма выплаты:", f"{vacation['payment_amount']:.2f}" if vacation['payment_amount'] else "-"),
                ("Дата выплаты:", vacation['payment_date'].strftime('%d.%m.%Y') if vacation['payment_date'] else "-"),
                ("Дата расчета:", vacation['calculation_date'].strftime('%d.%m.%Y')),
                ("Дата создания:", vacation['created_at'].strftime('%d.%m.%Y %H:%M:%S')),
                ("Дата обновления:", vacation['updated_at'].strftime('%d.%m.%Y %H:%M:%S') if vacation['updated_at'] else "-")
            ]:
                ttk.Label(main_frame, text=label_text, font=("Arial", 10, "bold")).grid(
                    row=row, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(main_frame, text=str(value)).grid(
                    row=row, column=1, sticky=tk.W, padx=5, pady=2)
                row += 1
            
            ttk.Label(main_frame, text="Примечания:", font=("Arial", 10, "bold")).grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=2)
            row += 1
            
            notes_text = tk.Text(main_frame, height=5, width=50, wrap=tk.WORD)
            notes_text.grid(row=row, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
            notes_text.insert(tk.END, vacation['notes'] if vacation['notes'] else "")
            notes_text.config(state=tk.DISABLED)
            
            ttk.Button(main_frame, text="Закрыть", command=details_window.destroy).grid(
                row=row+1, column=0, columnspan=2, pady=(15, 0))
        
        except Exception as e:
            logger.error(f"Ошибка при отображении деталей отпуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось отобразить детали отпуска: {str(e)}")
    
    def _export_vacation_report(self):
        """Экспорт отчета по отпускам"""
        try:
            year = int(self.year_var.get()) if self.year_var.get() else datetime.date.today().year
            
            format_dialog = tk.Toplevel()
            format_dialog.title("Выбор формата отчета")
            format_dialog.geometry("300x150")
            format_dialog.resizable(False, False)
            format_dialog.grab_set()
            
            format_dialog.update_idletasks()
            width = format_dialog.winfo_width()
            height = format_dialog.winfo_height()
            x = (format_dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (format_dialog.winfo_screenheight() // 2) - (height // 2)
            format_dialog.geometry(f"+{x}+{y}")
            
            ttk.Label(format_dialog, text="Выберите формат отчета:", font=("Arial", 10, "bold")).pack(pady=(15, 10))
            
            format_var = tk.StringVar(value="csv")
            ttk.Radiobutton(format_dialog, text="CSV", variable=format_var, value="csv").pack(anchor=tk.W, padx=20)
            ttk.Radiobutton(format_dialog, text="Текстовый отчет", variable=format_var, value="text").pack(anchor=tk.W, padx=20)
            
            def confirm_export():
                selected_format = format_var.get()
                format_dialog.destroy()
                
                file_extensions = [("CSV файлы", "*.csv")] if selected_format == "csv" else [("Текстовые файлы", "*.txt")]
                default_extension = ".csv" if selected_format == "csv" else ".txt"
                
                filename = f"отчет_по_отпускам_{year}{default_extension}"
                save_path = filedialog.asksaveasfilename(
                    defaultextension=default_extension,
                    filetypes=file_extensions,
                    title="Сохранить отчет как",
                    initialfile=filename
                )
                
                if not save_path:
                    return
                
                report_data = self.vacation_processor.export_vacation_report(year, selected_format)
                
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(report_data)
                
                messagebox.showinfo("Успех", f"Отчет успешно сохранен в файл:\n{save_path}")
            
            ttk.Button(format_dialog, text="Создать отчет", command=confirm_export).pack(pady=(10, 0))
            ttk.Button(format_dialog, text="Отмена", command=format_dialog.destroy).pack(pady=(5, 0))
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать отчет: {str(e)}")
    
    def _show_vacation_statistics(self):
        """Показать статистику по отпускам"""
        try:
            year = int(self.year_var.get()) if self.year_var.get() else datetime.date.today().year
            
            stats = self.vacation_processor.get_vacation_statistics(year)
            
            stats_window = tk.Toplevel()
            stats_window.title(f"Статистика отпусков за {year} год")
            stats_window.geometry("600x500")
            stats_window.grab_set()
            
            stats_window.update_idletasks()
            width = stats_window.winfo_width()
            height = stats_window.winfo_height()
            x = (stats_window.winfo_screenwidth() // 2) - (width // 2)
            y = (stats_window.winfo_screenheight() // 2) - (height // 2)
            stats_window.geometry(f"+{x}+{y}")
            
            main_frame = ttk.Frame(stats_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text=f"Статистика отпусков за {year} год", 
                    font=("Arial", 14, "bold")).pack(pady=(0, 15))
            
            general_frame = ttk.LabelFrame(main_frame, text="Общая статистика")
            general_frame.pack(fill=tk.X, pady=(0, 10))
            
            general_stats = stats['general']
            
            row = 0
            for label_text, value in [
                ("Всего отпусков:", general_stats['total_vacations']),
                ("Всего дней:", general_stats['total_days']),
                ("Общая сумма выплат:", f"{general_stats['total_payments']:.2f}" if general_stats['total_payments'] else "0.00"),
                ("Среднее кол-во дней на отпуск:", f"{general_stats['avg_days_per_vacation']:.2f}" if general_stats['avg_days_per_vacation'] else "0.00"),
                ("Средняя выплата на отпуск:", f"{general_stats['avg_payment']:.2f}" if general_stats['avg_payment'] else "0.00")
            ]:
                ttk.Label(general_frame, text=label_text, font=("Arial", 10, "bold")).grid(
                    row=row, column=0, sticky=tk.W, padx=10, pady=2)
                ttk.Label(general_frame, text=str(value)).grid(
                    row=row, column=1, sticky=tk.W, padx=10, pady=2)
                row += 1
            
            monthly_frame = ttk.LabelFrame(main_frame, text="Статистика по месяцам")
            monthly_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            columns = ("month", "month_name", "vacations_count", "total_days", "total_payments")
            monthly_tree = ttk.Treeview(monthly_frame, columns=columns, show="headings")
            
            monthly_tree.heading("month", text="Номер")
            monthly_tree.heading("month_name", text="Месяц")
            monthly_tree.heading("vacations_count", text="Кол-во отпусков")
            monthly_tree.heading("total_days", text="Всего дней")
            monthly_tree.heading("total_payments", text="Сумма выплат")
            
            monthly_tree.column("month", width=50, anchor=tk.CENTER)
            monthly_tree.column("month_name", width=100, anchor=tk.W)
            monthly_tree.column("vacations_count", width=120, anchor=tk.CENTER)
            monthly_tree.column("total_days", width=100, anchor=tk.CENTER)
            monthly_tree.column("total_payments", width=120, anchor=tk.E)
            
            for month_stat in stats['monthly']:
                monthly_tree.insert("", tk.END, values=(
                    int(month_stat['month']),
                    month_stat['month_name'],
                    month_stat['vacations_count'],
                    month_stat['total_days'],
                    f"{month_stat['total_payments']:.2f}" if month_stat['total_payments'] else "0.00"
                ))
            
            scrollbar = ttk.Scrollbar(monthly_frame, orient=tk.VERTICAL, command=monthly_tree.yview)
            monthly_tree.configure(yscrollcommand=scrollbar.set)
            
            monthly_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            ttk.Button(main_frame, text="Закрыть", command=stats_window.destroy).pack(pady=(0, 5))
            
        except Exception as e:
            logger.error(f"Ошибка при отображении статистики: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось отобразить статистику: {str(e)}")

    def _show_transfer_dialog(self):
        """Показать диалог для переноса дней отпуска"""
        if not self.current_teacher_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите преподавателя")
            return
        
        transfer_window = tk.Toplevel()
        transfer_window.title("Перенос дней отпуска")
        transfer_window.geometry("400x300")
        transfer_window.resizable(False, False)
        transfer_window.grab_set()
        
        main_frame = ttk.Frame(transfer_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Выбор года с которого переносятся дни
        ttk.Label(main_frame, text="Перенести с года:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.from_year_var = tk.StringVar()
        current_year = datetime.date.today().year
        years = [str(year) for year in range(current_year - 5, current_year)]
        self.from_year_combobox = ttk.Combobox(main_frame, textvariable=self.from_year_var, values=years, state="readonly")
        self.from_year_combobox.grid(row=0, column=1, padx=5, pady=5)
        if years:
            self.from_year_combobox.current(len(years) - 1)  # Устанавливаем текущий год по умолчанию
        
        # Выбор года на который переносятся дни
        ttk.Label(main_frame, text="Перенести на год:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.to_year_var = tk.StringVar()
        years = [str(year) for year in range(current_year, current_year + 5)]
        self.to_year_combobox = ttk.Combobox(main_frame, textvariable=self.to_year_var, values=years, state="readonly")
        self.to_year_combobox.grid(row=1, column=1, padx=5, pady=5)
        if years:
            self.to_year_combobox.current(0)  # Устанавливаем следующий год по умолчанию
        
        # Количество дней для переноса
        ttk.Label(main_frame, text="Количество дней:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.transfer_days_var = tk.StringVar(value="0")
        ttk.Entry(main_frame, textvariable=self.transfer_days_var, width=10).grid(row=2, column=1, padx=5, pady=5)
        
        # Кнопка переноса
        ttk.Button(main_frame, text="Перенести", command=self._transfer_vacation_days).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Кнопка отмены
        ttk.Button(main_frame, text="Отмена", command=transfer_window.destroy).grid(row=4, column=0, columnspan=2, pady=5)
    
    def _transfer_vacation_days(self):
        """Перенести дни отпуска"""
        try:
            from_year = int(self.from_year_var.get())
            to_year = int(self.to_year_var.get())
            days_count = int(self.transfer_days_var.get())
            
            if from_year >= to_year:
                messagebox.showerror("Ошибка", "Год 'с которого' должен быть меньше года 'на который'")
                return
            
            if days_count <= 0:
                messagebox.showerror("Ошибка", "Количество дней должно быть положительным")
                return
            
            remaining_days = self.vacation_processor.get_teacher_remaining_vacation_days(self.current_teacher_id, from_year)
            if days_count > remaining_days:
                messagebox.showerror("Ошибка", f"Нельзя перенести больше дней ({days_count}), чем осталось ({remaining_days}) за {from_year} год")
                return
            
            transfer_id = self.vacation_processor.transfer_vacation_days(self.current_teacher_id, from_year, to_year, days_count)
            messagebox.showinfo("Успех", f"Дни отпуска успешно перенесены (ID: {transfer_id})")
            self._on_teacher_selected(None)
            self._show_transfer_dialog().destroy()  # Закрываем диалог после успешного переноса
        except ValueError as ve:
            messagebox.showerror("Ошибка", "Пожалуйста, введите корректные числовые значения")
        except Exception as e:
            logger.error(f"Ошибка при переносе дней отпуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось перенести дни отпуска: {str(e)}")