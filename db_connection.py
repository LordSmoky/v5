import psycopg2
from psycopg2 import pool
import logging
from typing import Dict, List, Any, Optional, Tuple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Класс для управления подключениями к базе данных"""
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Инициализация пула соединений с базой данных
        
        :param db_config: словарь с параметрами подключения к БД
        """
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=db_config.get('host', 'localhost'),
                database=db_config.get('database', 'salary_calculator2'),
                user=db_config.get('user', 'postgres'),
                password=db_config.get('password', '123321445'),
                port=db_config.get('port', '5432')
            )
            logger.info("Пул соединений с базой данных успешно создан")
        except Exception as e:
            logger.error(f"Ошибка при создании пула соединений: {str(e)}")
            raise

    def get_connection(self):
        """Получить соединение из пула"""
        return self.connection_pool.getconn()
    
    def release_connection(self, connection):
        """Вернуть соединение в пул"""
        self.connection_pool.putconn(connection)
    
    def close_all_connections(self):
        """Закрыть все соединения в пуле"""
        self.connection_pool.closeall()
        logger.info("Все соединения закрыты")

    def get_repository(self, repo_type: str):
        """
        Получить репозиторий определенного типа
        
        :param repo_type: тип репозитория ('teacher', 'salary', 'reference')
        :return: экземпляр запрошенного репозитория
        """
        if repo_type.lower() == 'teacher':
            return TeacherRepository(self)
        elif repo_type.lower() == 'salary':
            return SalaryCalculationRepository(self)
        elif repo_type.lower() == 'reference':
            return ReferenceDataRepository(self)
        else:
            raise ValueError(f"Неизвестный тип репозитория: {repo_type}")
        
class TeacherRepository:
    """Класс для работы с данными преподавателей"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
    
    def get_all_teachers(self) -> List[Dict[str, Any]]:
        """
        Получить список всех преподавателей
        
        :return: список преподавателей
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        teachers = []
        
        try:
            cursor.execute("""
                SELECT t.id, t.name, t.hourly_rate, t.is_young_specialist, 
                       t.is_union_member, t.position, t.academic_degree, 
                       t.qualification_category, t.experience_years, 
                       t.hire_date, t.birth_date
                FROM teachers t
                ORDER BY t.name
            """)
            
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                teacher = dict(zip(columns, row))
                teachers.append(teacher)
                
            return teachers
        except Exception as e:
            logger.error(f"Ошибка при получении списка преподавателей: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def get_teacher_by_id(self, teacher_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить данные преподавателя по ID
        
        :param teacher_id: ID преподавателя
        :return: данные преподавателя или None
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT t.id, t.name, t.hourly_rate, t.is_young_specialist, 
                       t.is_union_member, t.position, t.academic_degree, 
                       t.qualification_category, t.experience_years, 
                       t.hire_date, t.birth_date
                FROM teachers t
                WHERE t.id = %s
            """, (teacher_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"Ошибка при получении данных преподавателя (id={teacher_id}): {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def add_teacher(self, teacher_data: Dict[str, Any]) -> int:
        """
        Добавить нового преподавателя
        
        :param teacher_data: данные преподавателя
        :return: ID нового преподавателя
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO teachers (
                    name, hourly_rate, is_young_specialist, is_union_member,
                    position, academic_degree, qualification_category,
                    experience_years, hire_date, birth_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """, (
                teacher_data.get('name'),
                teacher_data.get('hourly_rate'),
                teacher_data.get('is_young_specialist', False),
                teacher_data.get('is_union_member', False),
                teacher_data.get('position'),
                teacher_data.get('academic_degree'),
                teacher_data.get('qualification_category'),
                teacher_data.get('experience_years', 0),
                teacher_data.get('hire_date'),
                teacher_data.get('birth_date')
            ))
            
            teacher_id = cursor.fetchone()[0]
            connection.commit()
            logger.info(f"Добавлен новый преподаватель с ID: {teacher_id}")
            return teacher_id
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при добавлении преподавателя: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)

    def update_teacher(self, teacher_id: int, teacher_data: Dict[str, Any]) -> bool:
        """
        Обновить данные преподавателя
        
        :param teacher_id: ID преподавателя
        :param teacher_data: обновленные данные
        :return: True если обновление успешно, иначе False
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE teachers SET
                    name = %s,
                    hourly_rate = %s,
                    is_young_specialist = %s,
                    is_union_member = %s,
                    position = %s,
                    academic_degree = %s,
                    qualification_category = %s,
                    experience_years = %s,
                    hire_date = %s,
                    birth_date = %s
                WHERE id = %s
            """, (
                teacher_data.get('name'),
                teacher_data.get('hourly_rate'),
                teacher_data.get('is_young_specialist', False),
                teacher_data.get('is_union_member', False),
                teacher_data.get('position'),
                teacher_data.get('academic_degree'),
                teacher_data.get('qualification_category'),
                teacher_data.get('experience_years', 0),
                teacher_data.get('hire_date'),
                teacher_data.get('birth_date'),
                teacher_id
            ))
            
            updated = cursor.rowcount > 0
            connection.commit()
            if updated:
                logger.info(f"Обновлены данные преподавателя с ID: {teacher_id}")
            return updated
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при обновлении данных преподавателя (id={teacher_id}): {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)

    def delete_teacher(self, teacher_id: int) -> bool:
        """
        Удалить преподавателя
        
        :param teacher_id: ID преподавателя
        :return: True если удаление успешно, иначе False
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
            deleted = cursor.rowcount > 0
            connection.commit()
            if deleted:
                logger.info(f"Удален преподаватель с ID: {teacher_id}")
            return deleted
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при удалении преподавателя (id={teacher_id}): {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)

class SalaryCalculationRepository:
    """Класс для работы с расчетами зарплаты"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
    
    def get_calculations_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """
        Получить все расчеты для преподавателя
        
        :param teacher_id: ID преподавателя
        :return: список расчетов
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT *
                FROM salary_calculations
                WHERE teacher_id = %s
                ORDER BY calculation_date DESC
            """, (teacher_id,))
            
            columns = [desc[0] for desc in cursor.description]
            calculations = []
            for row in cursor.fetchall():
                calculation = dict(zip(columns, row))
                calculations.append(calculation)
                
            return calculations
        except Exception as e:
            logger.error(f"Ошибка при получении расчетов для препо��авателя (id={teacher_id}): {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)

    def get_calculations_by_teacher_and_period(self, teacher_id: int, start_date, end_date) -> List[Dict[str, Any]]:
        """
        Получить расчёты зарплат преподавателя за указанный период дат.
        
        :param teacher_id: ID преподавателя
        :param start_date: дата начала периода (Date, DateTime)
        :param end_date: дата окончания периода (Date, DateTime)
        :return: список расчётов
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT *
                FROM salary_calculations
                WHERE teacher_id = %s
                AND calculation_date BETWEEN %s AND %s
                ORDER BY calculation_date DESC
            """, (teacher_id, start_date, end_date))
            
            columns = [desc[0] for desc in cursor.description]
            calculations = []
            for row in cursor.fetchall():
                calculation = dict(zip(columns, row))
                calculations.append(calculation)
            return calculations
        except Exception as e:
            logger.error(f"Ошибка при получении расчетов за период: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def add_calculation(self, calculation_data: Dict[str, Any]) -> int:
        """
        Добавить новый расчет зарплаты
        
        :param calculation_data: данные расчета
        :return: ID нового расчета
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO salary_calculations (
                    teacher_id, calculation_date, hours_worked, sick_leave_hours,
                    absence_hours, bonus, tax_rate, gross_salary, net_salary,
                    vacation_days, vacation_pay, position_bonus, degree_bonus,
                    experience_bonus, category_bonus
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """, (
                calculation_data.get('teacher_id'),
                calculation_data.get('calculation_date'),
                calculation_data.get('hours_worked', 0),
                calculation_data.get('sick_leave_hours', 0),
                calculation_data.get('absence_hours', 0),
                calculation_data.get('bonus', 0),
                calculation_data.get('tax_rate', 0.13),
                calculation_data.get('gross_salary', 0),
                calculation_data.get('net_salary', 0),
                calculation_data.get('vacation_days', 0),
                calculation_data.get('vacation_pay', 0),
                calculation_data.get('position_bonus', 0),
                calculation_data.get('degree_bonus', 0),
                calculation_data.get('experience_bonus', 0),
                calculation_data.get('category_bonus', 0)
            ))
            
            calculation_id = cursor.fetchone()[0]
            connection.commit()
            logger.info(f"Добавлен новый расчет зарплаты с ID: {calculation_id}")
            return calculation_id
        except Exception as e:
            connection.rollback()
            logger.error(f"Ошибка при добавлении расчета зарплаты: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)

class ReferenceDataRepository:
    """Класс для работы со справочными данными (коэффициенты, надбавки и т.д.)"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
    
    def get_position_coefficients(self) -> Dict[str, float]:
        """
        Получить коэффициенты по должностям
        
        :return: словарь {должность: коэффициент}
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT position, coefficient FROM position_coefficients")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка при получении коэффициентов по должностям: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def get_academic_degree_bonuses(self) -> Dict[str, float]:
        """
        Получить надбавки за ученую степень
        
        :return: словарь {степень: процент надбавки}
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT degree, bonus_percent FROM academic_degree_bonuses")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка при получении надбавок за ученую степень: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def get_experience_bonuses(self) -> List[Tuple[int, Optional[int], float]]:
        """
        Получить надбавки за стаж
        
        :return: список кортежей (мин_лет, макс_лет, процент)
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT min_years, max_years, bonus_percent FROM experience_bonuses ORDER BY min_years")
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении надбавок за стаж: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def get_qualification_bonuses(self) -> Dict[str, float]:
        """
        Получить надбавки за квалификационную категорию
        
        :return: словарь {категория: процент надбавки}
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT category, bonus_percent FROM qualification_bonuses")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка при получении надбавок за квалификацию: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
    
    def get_vacation_days(self) -> Dict[str, Dict[str, int]]:
        """
        Получить информацию о днях отпуска по должностям
        
        :return: словарь {должность: {базовые_дни, доп_дни_степень, доп_дни_стаж}}
        """
        connection = self.db_connection.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("""
                SELECT position, base_days, additional_days_degree, additional_days_experience 
                FROM vacation_days
            """)
            
            result = {}
            for row in cursor.fetchall():
                position, base_days, add_days_degree, add_days_exp = row
                result[position] = {
                    'base_days': base_days,
                    'additional_days_degree': add_days_degree,
                    'additional_days_experience': add_days_exp
                }
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении дней отпуска: {str(e)}")
            raise
        finally:
            cursor.close()
            self.db_connection.release_connection(connection)
