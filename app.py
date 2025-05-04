import logging
import datetime
from typing import Dict, Any, List, Optional
from db_connection import DatabaseConnection, SalaryCalculationRepository, TeacherRepository
from salary_calculator import SalaryCalculator
from vacation_processor import VacationProcessor


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SalaryApp:
    """Основной класс приложения для расчета зарплаты, отпусков и больничных"""
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Инициализация приложения
        
        :param db_config: конфигурация подключения к базе данных
        """
        logger.info("Инициализация приложения")
        self.db_connection = DatabaseConnection(db_config)
        self.teacher_repo = TeacherRepository(self.db_connection)
        self.salary_calculator = SalaryCalculator(self.db_connection)
        self.vacation_processor = VacationProcessor(self.db_connection, self.salary_calculator)
    
    def close(self):
        """Закрытие приложения и освобождение ресурсов"""
        logger.info("Закрытие соединений с базой данных")
        self.db_connection.close_all_connections()
    
    # Методы для работы с преподавателями
    
    def get_all_teachers(self) -> List[Dict[str, Any]]:
        """
        Получить список всех преподавателей
        
        :return: список преподавателей
        """
        try:
            return self.teacher_repo.get_all_teachers()
        except Exception as e:
            logger.error(f"Ошибка при получении списка преподавателей: {str(e)}")
            raise
    
    def get_teacher_by_id(self, teacher_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить данные преподавателя по ID
        
        :param teacher_id: ID преподавателя
        :return: данные преподавателя или None
        """
        try:
            return self.teacher_repo.get_teacher_by_id(teacher_id)
        except Exception as e:
            logger.error(f"Ошибка при получении данных преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def add_teacher(self, teacher_data: Dict[str, Any]) -> int:
        """
        Добавить нового преподавателя
        
        :param teacher_data: данные преподавателя
        :return: ID нового преподавателя
        """
        try:
            required_fields = ['name', 'hourly_rate', 'hire_date']
            for field in required_fields:
                if field not in teacher_data:
                    raise ValueError(f"Отсутствует обязательное поле: {field}")
            
            return self.teacher_repo.add_teacher(teacher_data)
        except Exception as e:
            logger.error(f"Ошибка при добавлении преподавателя: {str(e)}")
            raise
    
    def update_teacher(self, teacher_id: int, teacher_data: Dict[str, Any]) -> bool:
        """
        Обновить данные преподавателя
        
        :param teacher_id: ID преподавателя
        :param teacher_data: обновленные данные
        :return: True если обновление успешно, иначе False
        """
        try:
            return self.teacher_repo.update_teacher(teacher_id, teacher_data)
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def delete_teacher(self, teacher_id: int) -> bool:
        """
        Удалить преподавателя
        
        :param teacher_id: ID преподавателя
        :return: True если удаление успешно, иначе False
        """
        try:
            return self.teacher_repo.delete_teacher(teacher_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    # Методы для расчета зарплаты
    
    def calculate_salary(self, teacher_id: int, calc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Рассчитать заработную плату преподавателя
        
        :param teacher_id: ID преподавателя
        :param calc_data: данные для расчета (часы, бонусы и т.д.)
        :return: полный расчет зарплаты
        """
        try:
            return self.salary_calculator.calculate_salary(teacher_id, calc_data)
        except Exception as e:
            logger.error(f"Ошибка при расчете зарплаты для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def save_salary_calculation(self, calculation_data: Dict[str, Any]) -> int:
        """
        Сохранить расчет зарплаты в базу данных
        
        :param calculation_data: данные расчета
        :return: ID сохраненного расчета
        """
        try:
            return self.salary_calculator.save_calculation(calculation_data)
        except Exception as e:
            logger.error(f"Ошибка при сохранении расчета зарплаты: {str(e)}")
            raise
    
    def get_teacher_salary_statistics(self, teacher_id: int, year: int) -> Dict[str, Any]:
        """
        Получить статистику по зарплате преподавателя за год
        
        :param teacher_id: ID преподавателя
        :param year: год для анализа
        :return: статистика по зарплате
        """
        try:
            return self.salary_calculator.get_teacher_statistics(teacher_id, year)
        except Exception as e:
            logger.error(f"Ошибка при получении статистики зарплаты для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    # Методы для работы с отпусками

    def get_salary_data(self, teacher_id, start_date=None, end_date=None):
        """
        Получает данные о зарплате преподавателя за указанный период
        
        :param teacher_id: ID преподавателя
        :param start_date: Начальная дата периода (может быть None для всех данных)
        :param end_date: Конечная дата периода (может быть None для всех данных)
        :return: Список с данными о расчетах зарплаты
        """
        try:
            # Подготавливаем запрос
            query = """
                SELECT * FROM salary_calculations 
                WHERE teacher_id = %s
            """
            params = [teacher_id]
            
            # Добавляем условия по датам, если они указаны
            if start_date:
                query += " AND calculation_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND calculation_date <= %s"
                params.append(end_date)
            
            # Сортируем по дате
            query += " ORDER BY calculation_date"
            
            # Выполняем запрос
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Преобразуем результаты в список словарей
                result = []
                for row in rows:
                    # Получаем названия столбцов
                    columns = [desc[0] for desc in cursor.description]
                    # Формируем словарь {название_столбца: значение}
                    result.append(dict(zip(columns, row)))
                
                return result
        except Exception as e:
            self.logger.error(f"Ошибка при получении данных о зарплате: {str(e)}")
            raise Exception(f"Не удалось получить данные о зарплате: {str(e)}")
        
    def get_teacher_vacation_days(self, teacher_id: int) -> int:
        """
        Получить положенное количество дней отпуска для преподавателя
        
        :param teacher_id: ID преподавателя
        :return: количество дней отпуска
        """
        try:
            return self.vacation_processor.get_teacher_vacation_days(teacher_id)
        except Exception as e:
            logger.error(f"Ошибка при получении дней отпуска для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def get_salary_data_for_period(self, teacher_id: int, start_date, end_date) -> List[Dict[str, Any]]:
        """
        Получить данные о зарплате преподавателя за указанный период
        
        :param teacher_id: ID преподавателя
        :param start_date: начальная дата периода
        :param end_date: конечная дата периода
        :return: список с данными о расчетах зарплаты
        """
        try:
            logger.info(f"Получение данных о зарплате для преподавателя ID={teacher_id} за период {start_date} - {end_date}")
            
            # Используем существующий репозиторий для запроса данных
            salary_repo = SalaryCalculationRepository(self.db_connection)
            
            # Получаем расчеты за указанный период
            calculations = salary_repo.get_calculations_by_teacher_and_period(teacher_id, start_date, end_date)
            
            return calculations
        except Exception as e:
            logger.error(f"Ошибка при получении данных о зарплате за период: {str(e)}")
            raise Exception(f"Не удалось получить данные о зарплате: {str(e)}")

    def get_teacher_remaining_vacation_days(self, teacher_id: int, year: int = None) -> int:
        """
        Получить количество оставшихся дней отпуска
        
        :param teacher_id: ID преподавателя
        :param year: год (если None, то текущий год)
        :return: количество оставшихся дней отпуска
        """
        try:
            return self.vacation_processor.get_teacher_remaining_vacation_days(teacher_id, year)
        except Exception as e:
            logger.error(f"Ошибка при получении оставшихся дней отпуска для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def schedule_vacation(self, teacher_id: int, start_date: datetime.date, 
                         end_date: datetime.date, vacation_type: str = 'основной',
                         notes: str = None) -> int:
        """
        Запланировать отпуск для преподавателя
        
        :param teacher_id: ID преподавателя
        :param start_date: дата начала отпуска
        :param end_date: дата окончания отпуска
        :param vacation_type: тип отпуска
        :param notes: примечания
        :return: ID записи отпуска
        """
        try:
            return self.vacation_processor.schedule_vacation(teacher_id, start_date, end_date, vacation_type, notes)
        except Exception as e:
            logger.error(f"Ошибка при планировании отпуска для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def cancel_vacation(self, vacation_id: int) -> bool:
        """
        Отменить запланированный отпуск
        
        :param vacation_id: ID отпуска
        :return: True если отпуск успешно отменен, иначе False
        """
        try:
            return self.vacation_processor.cancel_vacation(vacation_id)
        except Exception as e:
            logger.error(f"Ошибка при отмене отпуска (id={vacation_id}): {str(e)}")
            raise
    
    def calculate_vacation_payment(self, vacation_id: int) -> Dict[str, Any]:
        """
        Рассчитать выплату за отпуск
        
        :param vacation_id: ID отпуска
        :return: информация о расчете отпускных
        """
        try:
            return self.vacation_processor.calculate_vacation_payment(vacation_id)
        except Exception as e:
            logger.error(f"Ошибка при расчете отпускных (id={vacation_id}): {str(e)}")
            raise
    
    def get_teacher_vacations(self, teacher_id: int, year: int = None, 
                            include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """
        Получить список отпусков преподавателя
        
        :param teacher_id: ID преподавателя
        :param year: год (если None, то все годы)
        :param include_cancelled: включать ли отмененные отпуска
        :return: список отпусков
        """
        try:
            return self.vacation_processor.get_teacher_vacations(teacher_id, year, include_cancelled)
        except Exception as e:
            logger.error(f"Ошибка при получении списка отпусков для преподавателя (id={teacher_id}): {str(e)}")
            raise
    
    def suggest_optimal_vacation_distribution(self, teacher_id: int, year: int = None) -> List[Dict[str, Any]]:
        """
        Предложить оптимальное распределение отпуска
        
        :param teacher_id: ID преподавателя
        :param year: год (если None, то текущий год)
        :return: список предлагаемых периодов отпуска
        """
        try:
            return self.vacation_processor.suggest_optimal_vacation_distribution(teacher_id, year)
        except Exception as e:
            logger.error(f"Ошибка при формировании оптимального распределения отпуска (id={teacher_id}): {str(e)}")
            raise
    
    
    # Общие методы для отчетности
    
    def export_vacation_report(self, year: int = None, format: str = 'csv') -> str:
        """
        Экспорт отчета по отпускам
        
        :param year: год для отчета (если None, то текущий год)
        :param format: формат отчета ('csv' или 'text')
        :return: отчет в выбранном формате
        """
        try:
            return self.vacation_processor.export_vacation_report(year, format)
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета по отпускам: {str(e)}")
            raise

    
    def generate_monthly_payroll_report(self, year: int, month: int, format: str = 'csv') -> str:
        """
        Генерация отчета по заработной плате за месяц
        
        :param year: год
        :param month: месяц (1-12)
        :param format: формат отчета ('csv' или 'text')
        :return: отчет в выбранном формате
        """
        try:
            # Получаем всех преподавателей
            teachers = self.get_all_teachers()
            
            # Определяем период
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            month_start = datetime.date(year, month, 1)
            month_end = datetime.date(year, month, last_day)
            
            # Формируем отчет
            if format == 'csv':
                report = "ID,ФИО,Должность,Ставка,Отработано часов,Больничные часы,Отсутствие часы,Бонус,Налог,Валовая зарплата,Чистая зарплата,Отпускные\n"
                
                for teacher in teachers:
                    # В реальном приложении здесь должен быть запрос к базе данных для получения расчетов за месяц
                    # Упрощенная реализация для примера
                    report += f"{teacher['id']},{teacher['name']},{teacher.get('position', '')},{teacher['hourly_rate']},,,,,,,,,\n"
            else:
                report = f"ОТЧЕТ ПО ЗАРАБОТНОЙ ПЛАТЕ ЗА {month}.{year}\n\n"
                
                total_gross = 0
                total_net = 0
                
                for teacher in teachers:
                    report += f"Преподаватель: {teacher['name']} (ID: {teacher['id']})\n"
                    report += f"Должность: {teacher.get('position', 'Не указана')}\n"
                    report += f"Ставка: {teacher['hourly_rate']} руб/час\n"
                    report += "-------------------\n\n"
                
                report += f"\nИТОГО: {total_gross} руб. (до вычета налогов), {total_net} руб. (после вычета налогов)\n"
            
            return report
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета по заработной плате: {str(e)}")
            raise
        
    def get_teacher_salary_data(self, teacher_id, start_date, end_date):
        """
        Получение данных о зарплате преподавателя за указанный период    

        :param teacher_id: ID преподавателя
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Список словарей с данными о расчетах зарплаты
        """
        # Реализация запроса к базе данных
        
    def get_all_teachers_salary_data(self, start_date, end_date):
        """
        Получение данных о зарплате всех преподавателей за указанный период
        
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Список словарей с данными о расчетах зарплаты по преподавателям
        """
        # Реализация запроса к базе данных
        
    def get_teacher_vacation_data(self, teacher_id, start_date, end_date):
        """
        Получение данных об отпусках преподавателя за указанный период
        
        :param teacher_id: ID преподавателя
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Словарь с данными об отпусках
        """
        # Реализация запроса к базе данных
        
    def get_all_teachers_vacation_data(self, start_date, end_date):
        """
        Получение данных об отпусках всех преподавателей за указанный период
        
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Список словарей с данными об отпусках по преподавателям
        """
        # Реализация запроса к базе данных
        
    def get_vacation_calendar(self, start_date, end_date):
        """
        Получение календарного графика отпусков за указанный период
        
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Данные для календарного графика отпусков
        """
        # Реализация запроса к базе данных

        
    def get_all_teachers_sick_leave_data(self, start_date, end_date):
        """
        Получение данных о больничных всех преподавателей за указанный период
        
        :param start_date: Начальная дата периода
        :param end_date: Конечная дата периода
        :return: Список словарей с данными о больничных по преподавателям
        """

# Пример использования приложения
if __name__ == "__main__":
    # Конфигурация подключения к базе данных
    db_config = {
        'host': 'localhost',
        'database': 'salary_calculator2',
        'user': 'postgres',
        'password': '123321445',
        'port': '5432'
    }
    
    try:
        # Инициализация приложения
        app = SalaryApp(db_config)
        
        # Пример использования - получение списка преподавателей
        teachers = app.get_all_teachers()
        print(f"Всего преподавателей: {len(teachers)}")
        
        for teacher in teachers:
            print(f"ID: {teacher['id']}, Имя: {teacher['name']}, Должность: {teacher.get('position', 'Не указана')}")
        
        # Корректное завершение работы приложения
        app.close()
    except Exception as e:
        logger.error(f"Ошибка при работе приложения: {str(e)}")


