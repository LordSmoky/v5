import datetime
from typing import Dict, Any, List, Optional
import logging
from decimal import Decimal, ROUND_HALF_UP
import db_connection as db
from salary_calculator import SalaryCalculator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VacationProcessor:
    """Класс для обработки отпусков преподавателей"""
    
    def __init__(self, db_conn: db.DatabaseConnection, salary_calculator: SalaryCalculator = None):
        """
        Инициализация процессора отпусков
        
        :param db_conn: объект подключения к базе данных
        :param salary_calculator: объект калькулятора зарплаты (опционально)
        """
        self.db_conn = db_conn
        self.teacher_repo = db.TeacherRepository(db_conn)
        self.salary_repo = db.SalaryCalculationRepository(db_conn)
        self.reference_repo = db.ReferenceDataRepository(db_conn)
        
        if salary_calculator is None:
            self.salary_calculator = SalaryCalculator(db_conn)
        else:
            self.salary_calculator = salary_calculator
        
        self._create_vacation_table_if_not_exists()
        self._create_vacation_transfer_table_if_not_exists()
    
    def _create_vacation_table_if_not_exists(self):
        """Создание таблицы для хранения информации об отпусках, если она не существует"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teacher_vacations (
                    id SERIAL PRIMARY KEY,
                    teacher_id INTEGER REFERENCES teachers(id) ON DELETE CASCADE,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    days_count INTEGER NOT NULL,
                    vacation_type VARCHAR(50) NOT NULL DEFAULT 'основной',
                    status VARCHAR(20) NOT NULL DEFAULT 'запланирован',
                    payment_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    payment_date DATE,
                    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vacation_teacher_id 
                ON teacher_vacations(teacher_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vacation_dates 
                ON teacher_vacations(start_date, end_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vacation_status 
                ON teacher_vacations(status)
            """)
            
            connection.commit()
            logger.info("Таблица для хранения информации об отпусках проверена/создана")
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при создании таблицы отпусков: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def _create_vacation_transfer_table_if_not_exists(self):
        """Создание таблицы для хранения переносов дней отпуска"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vacation_days_transfer (
                    id SERIAL PRIMARY KEY,
                    teacher_id INTEGER REFERENCES teachers(id) ON DELETE CASCADE,
                    from_year INTEGER NOT NULL,
                    to_year INTEGER NOT NULL,
                    days_count INTEGER NOT NULL CHECK (days_count > 0),
                    transfer_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transfer_teacher_id 
                ON vacation_days_transfer(teacher_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transfer_years 
                ON vacation_days_transfer(from_year, to_year)
            """)
            
            connection.commit()
            logger.info("Таблица для переносов дней отпуска проверена/создана")
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при создании таблицы переносов отпусков: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_teacher_vacation_days(self, teacher_id: int) -> int:
        """Получить базовое количество дней отпуска для преподавателя"""
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        return self.salary_calculator._get_vacation_days(teacher)
    
    def get_teacher_used_vacation_days(self, teacher_id: int, year: int = None) -> int:
        """Получить количество использованных дней отпуска за год"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            year_condition = ""
            params = [teacher_id]
            
            if year is not None:
                year_start = datetime.date(year, 1, 1)
                year_end = datetime.date(year, 12, 31)
                year_condition = "AND (start_date BETWEEN %s AND %s OR end_date BETWEEN %s AND %s)"
                params.extend([year_start, year_end, year_start, year_end])
            
            cursor.execute(f"""
                SELECT COALESCE(SUM(days_count), 0)
                FROM teacher_vacations
                WHERE teacher_id = %s 
                AND status IN ('запланирован', 'использован', 'оплачен')
                {year_condition}
            """, params)
            
            used_days = cursor.fetchone()[0]
            return used_days if used_days else 0
        except Exception as e:
            logger.error(f"Ошибка при получении использованных дней отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_transferred_vacation_days_in(self, teacher_id: int, year: int) -> int:
        """Получить количество дней, перенесенных на указанный год"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT COALESCE(SUM(days_count), 0)
                FROM vacation_days_transfer
                WHERE teacher_id = %s AND to_year = %s
            """, (teacher_id, year))
            
            transferred_days = cursor.fetchone()[0]
            return transferred_days if transferred_days else 0
        except Exception as e:
            logger.error(f"Ошибка при получении перенесенных дней на год: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_transferred_vacation_days_out(self, teacher_id: int, year: int) -> int:
        """Получить количество дней, перенесенных с указанного года"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT COALESCE(SUM(days_count), 0)
                FROM vacation_days_transfer
                WHERE teacher_id = %s AND from_year = %s
            """, (teacher_id, year))
            
            transferred_days = cursor.fetchone()[0]
            return transferred_days if transferred_days else 0
        except Exception as e:
            logger.error(f"Ошибка при получении перенесенных дней с года: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_teacher_remaining_vacation_days(self, teacher_id: int, year: int = None) -> int:
        """Получить количество оставшихся дней отпуска с учетом переносов"""
        if year is None:
            year = datetime.date.today().year
        
        base_days = self.get_teacher_vacation_days(teacher_id)
        used_days = self.get_teacher_used_vacation_days(teacher_id, year)
        transferred_in = self.get_transferred_vacation_days_in(teacher_id, year)
        transferred_out = self.get_transferred_vacation_days_out(teacher_id, year)
        
        remaining_days = base_days - used_days + transferred_in - transferred_out
        return max(0, remaining_days)
    
    def transfer_vacation_days(self, teacher_id: int, from_year: int, to_year: int, days_count: int) -> int:
        """Перенести дни отпуска с одного года на другой"""
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        if from_year >= to_year:
            raise ValueError("Год 'с которого' должен быть меньше года 'на который'")
        
        remaining_days = self.get_teacher_remaining_vacation_days(teacher_id, from_year)
        if days_count > remaining_days:
            raise ValueError(f"Недостаточно дней для переноса. Доступно: {remaining_days}, запрошено: {days_count}")
        
        if days_count <= 0:
            raise ValueError("Количество дней для переноса должно быть положительным")
        
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO vacation_days_transfer (
                    teacher_id, from_year, to_year, days_count, notes
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                teacher_id, from_year, to_year, days_count,
                f"Перенос {days_count} дней с {from_year} на {to_year}"
            ))
            
            transfer_id = cursor.fetchone()[0]
            connection.commit()
            
            logger.info(f"Перенесено {days_count} дней отпуска для {teacher['name']} (ID: {teacher_id}) с {from_year} на {to_year}")
            return transfer_id
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при переносе дней отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def schedule_vacation(self, teacher_id: int, start_date: datetime.date, 
                         end_date: datetime.date, vacation_type: str = 'основной',
                         notes: str = None) -> int:
        """Запланировать отпуск для преподавателя"""
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        if start_date > end_date:
            raise ValueError("Дата начала не может быть позже даты окончания")
        
        if self._has_overlapping_vacations(teacher_id, start_date, end_date):
            raise ValueError("Указанный период пересекается с другими отпусками")
        
        days_count = (end_date - start_date).days + 1
        vacation_year = start_date.year
        remaining_days = self.get_teacher_remaining_vacation_days(teacher_id, vacation_year)
        
        if days_count > remaining_days:
            raise ValueError(f"Недостаточно дней отпуска. Доступно: {remaining_days}, запрошено: {days_count}")
        
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO teacher_vacations (
                    teacher_id, start_date, end_date, days_count, 
                    vacation_type, status, notes, calculation_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                teacher_id, start_date, end_date, days_count,
                vacation_type, 'запланирован', notes, datetime.date.today()
            ))
            
            vacation_id = cursor.fetchone()[0]
            connection.commit()
            
            logger.info(f"Запланирован отпуск для {teacher['name']} (ID: {teacher_id}) с {start_date} по {end_date}")
            return vacation_id
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при планировании отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def _has_overlapping_vacations(self, teacher_id: int, start_date: datetime.date, 
                                 end_date: datetime.date) -> bool:
        """Проверка на пересечение с другими отпусками"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM teacher_vacations
                WHERE teacher_id = %s
                AND status IN ('запланирован', 'использован', 'оплачен')
                AND (
                    (start_date <= %s AND end_date >= %s) OR
                    (start_date <= %s AND end_date >= %s) OR
                    (start_date >= %s AND end_date <= %s)
                )
            """, (
                teacher_id, 
                start_date, start_date,
                end_date, end_date,
                start_date, end_date
            ))
            
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"Ошибка при проверке пересечения отпусков: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def cancel_vacation(self, vacation_id: int) -> bool:
        """Отменить запланированный отпуск"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT v.id, t.id as teacher_id, t.name as teacher_name, v.status
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE v.id = %s
            """, (vacation_id,))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Отпуск с ID {vacation_id} не найден")
                return False
            
            _, teacher_id, teacher_name, status = result
            
            if status != 'запланирован':
                logger.warning(f"Невозможно отменить отпуск с ID {vacation_id}, статус: {status}")
                return False
            
            cursor.execute("""
                UPDATE teacher_vacations
                SET status = 'отменен', updated_at = NOW()
                WHERE id = %s
            """, (vacation_id,))
            
            connection.commit()
            logger.info(f"Отменен отпуск с ID {vacation_id} для {teacher_name} (ID: {teacher_id})")
            return True
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при отмене отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def mark_vacation_as_used(self, vacation_id: int) -> bool:
        """Отметить отпуск как использованный"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT v.id, t.id as teacher_id, t.name as teacher_name, v.status
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE v.id = %s
            """, (vacation_id,))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Отпуск с ID {vacation_id} не найден")
                return False
            
            _, teacher_id, teacher_name, status = result
            
            if status != 'запланирован':
                logger.warning(f"Невозможно отметить отпуск с ID {vacation_id}, статус: {status}")
                return False
            
            cursor.execute("""
                UPDATE teacher_vacations
                SET status = 'использован', updated_at = NOW()
                WHERE id = %s
            """, (vacation_id,))
            
            connection.commit()
            logger.info(f"Отпуск с ID {vacation_id} для {teacher_name} (ID: {teacher_id}) отмечен как использованный")
            return True
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при изменении статуса отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def calculate_vacation_payment(self, vacation_id: int) -> Dict[str, Any]:
        """Рассчитать выплату за отпуск"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT v.id, v.teacher_id, t.name as teacher_name, 
                       v.start_date, v.end_date, v.days_count, v.status
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE v.id = %s
            """, (vacation_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Отпуск с ID {vacation_id} не найден")
            
            vacation_id, teacher_id, teacher_name, start_date, end_date, days_count, status = result
            
            if status not in ('запланирован', 'использован'):
                raise ValueError(f"Невозможно рассчитать выплату для статуса: {status}")
            
            payment_info = self.salary_calculator.calculate_vacation_pay(
                teacher_id, start_date, end_date)
            
            cursor.execute("""
                UPDATE teacher_vacations
                SET payment_amount = %s, 
                    status = 'оплачен', 
                    payment_date = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                payment_info['gross_vacation_pay'],
                datetime.date.today(),
                vacation_id
            ))
            
            connection.commit()
            logger.info(f"Рассчитаны отпускные для отпуска ID {vacation_id} для {teacher_name} (ID: {teacher_id})")
            
            payment_info.update({
                'vacation_id': vacation_id,
                'calculation_date': datetime.date.today(),
                'days_count': days_count
            })
            return payment_info
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при расчете отпускных: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_teacher_vacations(self, teacher_id: int, year: int = None, 
                            include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """Получить список отпусков преподавателя"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            conditions = ["teacher_id = %s"]
            params = [teacher_id]
            
            if year is not None:
                conditions.append("(EXTRACT(YEAR FROM start_date) = %s OR EXTRACT(YEAR FROM end_date) = %s)")
                params.extend([year, year])
            
            if not include_cancelled:
                conditions.append("status != 'отменен'")
            
            where_clause = " AND ".join(conditions)
            
            cursor.execute(f"""
                SELECT v.id, v.teacher_id, t.name as teacher_name,
                       v.start_date, v.end_date, v.days_count,
                       v.vacation_type, v.status, v.payment_amount,
                       v.payment_date, v.calculation_date, v.notes,
                       v.created_at, v.updated_at
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE {where_clause}
                ORDER BY v.start_date DESC
            """, params)
            
            columns = [desc[0] for desc in cursor.description]
            vacations = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return vacations
        except Exception as e:
            logger.error(f"Ошибка при получении списка отпусков: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_vacation_by_id(self, vacation_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию об отпуске по ID"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT v.id, v.teacher_id, t.name as teacher_name,
                       v.start_date, v.end_date, v.days_count,
                       v.vacation_type, v.status, v.payment_amount,
                       v.payment_date, v.calculation_date, v.notes,
                       v.created_at, v.updated_at
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE v.id = %s
            """, (vacation_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"Ошибка при получении информации об отпуске: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_all_current_vacations(self, include_future: bool = True, 
                                include_past_days: int = 0) -> List[Dict[str, Any]]:
        """Получить список всех текущих и будущих отпусков"""
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            today = datetime.date.today()
            past_date = today - datetime.timedelta(days=include_past_days)
            
            conditions = ["status IN ('запланирован', 'использован', 'оплачен')"]
            params = []
            
            if include_future and include_past_days > 0:
                conditions.append("end_date >= %s")
                params.append(past_date)
            elif include_future:
                conditions.append("end_date >= %s")
                params.append(today)
            else:
                conditions.append("start_date <= %s AND end_date >= %s")
                params.extend([today, past_date])
            
            where_clause = " AND ".join(conditions)
            
            cursor.execute(f"""
                SELECT v.id, v.teacher_id, t.name as teacher_name,
                       v.start_date, v.end_date, v.days_count,
                       v.vacation_type, v.status, v.payment_amount,
                       v.payment_date, v.calculation_date, v.notes
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE {where_clause}
                ORDER BY v.start_date
            """, params)
            
            columns = [desc[0] for desc in cursor.description]
            vacations = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return vacations
        except Exception as e:
            logger.error(f"Ошибка при получении списка текущих отпусков: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def get_vacation_statistics(self, year: int = None) -> Dict[str, Any]:
        """Получить статистику по отпускам"""
        if year is None:
            year = datetime.date.today().year
        
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_vacations,
                    SUM(days_count) as total_days,
                    SUM(payment_amount) as total_payments,
                    ROUND(AVG(days_count), 2) as avg_days_per_vacation,
                    ROUND(AVG(payment_amount), 2) as avg_payment
                FROM teacher_vacations
                WHERE EXTRACT(YEAR FROM start_date) = %s
                AND status != 'отменен'
            """, (year,))
            
            general_stats = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
            
            cursor.execute("""
                SELECT 
                    EXTRACT(MONTH FROM start_date) as month,
                    COUNT(*) as vacations_count,
                    SUM(days_count) as total_days,
                    SUM(payment_amount) as total_payments
                FROM teacher_vacations
                WHERE EXTRACT(YEAR FROM start_date) = %s
                AND status != 'отменен'
                GROUP BY EXTRACT(MONTH FROM start_date)
                ORDER BY EXTRACT(MONTH FROM start_date)
            """, (year,))
            
            monthly_stats = []
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                month_stat = dict(zip(columns, row))
                month_stat['month_name'] = self._get_month_name(int(month_stat['month']))
                monthly_stats.append(month_stat)
            
            return {
                'year': year,
                'general': general_stats,
                'monthly': monthly_stats
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики по отпускам: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def _get_month_name(self, month_number: int) -> str:
        """Получить название месяца на русском языке"""
        month_names = {
            1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 
            6: 'Июнь', 7: 'Июль', 8: 'Август', 9: 'Сентябрь', 10: 'Октябрь', 
            11: 'Ноябрь', 12: 'Декабрь'
        }
        return month_names.get(month_number, f"Месяц {month_number}")
    
    def export_vacation_report(self, year: int = None, format: str = 'csv') -> str:
        """Экспорт отчета по отпускам"""
        if year is None:
            year = datetime.date.today().year
        
        connection = self.db_conn.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT t.name as teacher_name, v.start_date, v.end_date, 
                       v.days_count, v.vacation_type, v.status, v.payment_amount
                FROM teacher_vacations v
                JOIN teachers t ON v.teacher_id = t.id
                WHERE EXTRACT(YEAR FROM start_date) = %s
                AND status != 'отменен'
                ORDER BY t.name, v.start_date
            """, (year,))
            
            vacations = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
            
            if format == 'csv':
                return self._generate_csv_report(vacations)
            else:
                return self._generate_text_report(vacations, year)
        except Exception as e:
            logger.error(f"Ошибка при экспорте отчета по отпускам: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_conn.release_connection(connection)
    
    def _generate_csv_report(self, vacations: List[Dict[str, Any]]) -> str:
        """Генерация отчета в формате CSV"""
        if not vacations:
            return "ФИО,Дата начала,Дата окончания,Количество дней,Тип отпуска,Статус,Сумма выплаты\n"
        
        csv_report = "ФИО,Дата начала,Дата окончания,Количество дней,Тип отпуска,Статус,Сумма выплаты\n"
        for vacation in vacations:
            csv_report += (
                f"{vacation['teacher_name']},"
                f"{vacation['start_date'].strftime('%d.%m.%Y')},"
                f"{vacation['end_date'].strftime('%d.%m.%Y')},"
                f"{vacation['days_count']},"
                f"{vacation['vacation_type']},"
                f"{vacation['status']},"
                f"{vacation['payment_amount']}\n"
            )
        return csv_report
    
    def _generate_text_report(self, vacations: List[Dict[str, Any]], year: int) -> str:
        """Генерация отчета в текстовом формате"""
        if not vacations:
            return f"ОТЧЕТ ПО ОТПУСКАМ ЗА {year} ГОД\n\nОтпуска не найдены."
        
        report = f"ОТЧЕТ ПО ОТПУСКАМ ЗА {year} ГОД\n{'=' * 80}\n\n"
        teachers_vacations = {}
        for vacation in vacations:
            teacher_name = vacation['teacher_name']
            if teacher_name not in teachers_vacations:
                teachers_vacations[teacher_name] = []
            teachers_vacations[teacher_name].append(vacation)
        
        for teacher_name, teacher_vacations in sorted(teachers_vacations.items()):
            report += f"Преподаватель: {teacher_name}\n{'-' * 40}\n"
            total_days, total_payment = 0, 0
            
            for vacation in sorted(teacher_vacations, key=lambda v: v['start_date']):
                start_date = vacation['start_date'].strftime('%d.%m.%Y')
                end_date = vacation['end_date'].strftime('%d.%m.%Y')
                report += f"Период: {start_date} - {end_date} ({vacation['days_count']} дн.), "
                report += f"тип: {vacation['vacation_type']}, статус: {vacation['status']}\n"
                if vacation['payment_amount'] > 0:
                    report += f"Сумма выплаты: {vacation['payment_amount']:.2f} руб.\n"
                total_days += vacation['days_count']
                total_payment += vacation['payment_amount']
            
            report += f"\nИтого: {total_days} дней, выплачено: {total_payment:.2f} руб.\n\n{'=' * 80}\n\n"
        
        total_vacations = len(vacations)
        total_days = sum(v['days_count'] for v in vacations)
        total_payment = sum(v['payment_amount'] for v in vacations)
        report += f"ИТОГО ПО ВСЕМ ПРЕПОДАВАТЕЛЯМ ({len(teachers_vacations)}):\n"
        report += f"Всего отпусков: {total_vacations}\nВсего дней: {total_days}\n"
        report += f"Всего выплачено: {total_payment:.2f} руб.\n"
        return report

    def suggest_optimal_vacation_distribution(self, teacher_id: int, year: int = None) -> List[Dict[str, Any]]:
        """Предложить оптимальное распределение отпуска"""
        if year is None:
            year = datetime.date.today().year
        
        available_days = self.get_teacher_remaining_vacation_days(teacher_id, year)
        if available_days <= 0:
            return []
        
        # Здесь можно добавить логику для предложения оптимальных периодов,
        # но для простоты оставим заглушку
        return [{'start': datetime.date(year, 7, 1), 'end': datetime.date(year, 7, available_days), 'days': available_days}]