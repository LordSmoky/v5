import datetime
from typing import Dict, Any, Optional, List, Tuple
import logging
from decimal import Decimal, ROUND_HALF_UP
import db_connection as db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SalaryCalculator:
    """Класс для расчета заработной платы преподавателей в системе образования"""
    
    def __init__(self, db_conn: db.DatabaseConnection):
        """
        Инициализация калькулятора зарплаты
        
        :param db_conn: объект подключения к базе данных
        """
        self.db_conn = db_conn
        self.teacher_repo = db.TeacherRepository(db_conn)
        self.salary_repo = db.SalaryCalculationRepository(db_conn)
        self.reference_repo = db.ReferenceDataRepository(db_conn)
        
        # Загрузка справочных данных
        self._load_reference_data()
        
        # Стандартная ставка налога подоходного налога в РБ - 13%
        #Включёнт подоходный налог, а так же пенсионные взносы
        self.standard_tax_rate = Decimal('0.13')
    
    def _load_reference_data(self):
        """Загрузка справочных данных из базы"""
        try:
            self.position_coefficients = self.reference_repo.get_position_coefficients()
            self.degree_bonuses = self.reference_repo.get_academic_degree_bonuses()
            self.experience_bonuses = self.reference_repo.get_experience_bonuses()
            self.qualification_bonuses = self.reference_repo.get_qualification_bonuses()
            self.vacation_days_info = self.reference_repo.get_vacation_days()
            logger.info("Справочные данные успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка при загрузке справочных данных: {str(e)}")
            raise
    
    def _get_position_coefficient(self, position: str) -> Decimal:
        """
        Получить коэффициент по должности
        
        :param position: должность
        :return: коэффициент должности
        """
        if not position:
            return Decimal('1.0')
        return Decimal(str(self.position_coefficients.get(position.lower(), 1.0)))
    
    def _get_degree_bonus_percent(self, degree: Optional[str]) -> Decimal:
        """
        Получить процент надбавки за ученую степень
        
        :param degree: ученая степень
        :return: процент надбавки (от 0 до 100)
        """
        if not degree:
            return Decimal('0.0')
        return Decimal(str(self.degree_bonuses.get(degree.lower(), 0.0)))
    
    def _get_experience_bonus_percent(self, years: int) -> Decimal:
        """
        Получить процент надбавки за стаж
        
        :param years: количество лет стажа
        :return: процент надбавки (от 0 до 100)
        """
        for min_years, max_years, bonus_percent in self.experience_bonuses:
            if max_years is None:
                if years >= min_years:
                    return Decimal(str(bonus_percent))
            elif min_years <= years < max_years:
                return Decimal(str(bonus_percent))
        return Decimal('0.0')
    
    def _get_qualification_bonus_percent(self, category: Optional[str]) -> Decimal:
        """
        Получить процент надбавки за квалификационную категорию
        
        :param category: категория
        :return: процент надбавки (от 0 до 100)
        """
        if not category:
            return Decimal('0.0')
        return Decimal(str(self.qualification_bonuses.get(category.lower(), 0.0)))
    
    def _get_vacation_days(self, teacher_data: Dict[str, Any]) -> int:
        """
        Расчет количества дней отпуска
        
        :param teacher_data: данные преподавателя
        :return: количество дней отпуска
        """
        position = teacher_data.get('position', '').lower()
        vacation_info = self.vacation_days_info.get(position, {
            'base_days': 28,
            'additional_days_degree': 0,
            'additional_days_experience': 0
        })
        
        # Базовое количество дней
        total_days = vacation_info['base_days']
        
        # Дополнительные дни за ученую степень
        if teacher_data.get('academic_degree'):
            total_days += vacation_info['additional_days_degree']
        
        # Дополнительные дни за стаж
        if teacher_data.get('experience_years', 0) >= 5:
            total_days += vacation_info['additional_days_experience']
        
        # Если молодой специалист, то +3 дня
        if teacher_data.get('is_young_specialist', False):
            total_days += 3
        
        return total_days
    
    def calculate_salary(self, teacher_id: int, calc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Рассчитать заработную плату преподавателя
        
        :param teacher_id: ID преподавателя
        :param calc_data: данные для расчета (часы, бонусы и т.д.)
        :return: полный расчет зарплаты
        """
        # Получение данных преподавателя
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        # Преобразование числовых значений в Decimal для точных расчетов
        hourly_rate = Decimal(str(teacher['hourly_rate']))
        
        # Базовые параметры расчета
        hours_worked = Decimal(str(calc_data.get('hours_worked', 0)))
        sick_leave_hours = Decimal(str(calc_data.get('sick_leave_hours', 0)))
        absence_hours = Decimal(str(calc_data.get('absence_hours', 0)))
        bonus = Decimal(str(calc_data.get('bonus', 0)))
        tax_rate_from_input = Decimal(str(calc_data.get('tax_rate', self.standard_tax_rate * 100)))
        tax_rate = tax_rate_from_input / Decimal('100.0')
        calculation_date = calc_data.get('calculation_date', datetime.date.today())
        
        # Проверка корректности данных
        if hours_worked < 0 or sick_leave_hours < 0 or absence_hours < 0:
            raise ValueError("Количество часов не может быть отрицательным")
        
        # Р��счет базовой зарплаты по часам
        base_salary = hours_worked * hourly_rate
        
        # Расчет надбавок
        position_coefficient = self._get_position_coefficient(teacher.get('position', ''))
        position_bonus = base_salary * (position_coefficient - Decimal('1.0'))
        
        degree_bonus_percent = self._get_degree_bonus_percent(teacher.get('academic_degree'))
        degree_bonus = base_salary * (degree_bonus_percent / Decimal('100.0'))
        
        experience_bonus_percent = self._get_experience_bonus_percent(teacher.get('experience_years', 0))
        experience_bonus = base_salary * (experience_bonus_percent / Decimal('100.0'))
        
        qualification_bonus_percent = self._get_qualification_bonus_percent(teacher.get('qualification_category'))
        category_bonus = base_salary * (qualification_bonus_percent / Decimal('100.0'))
        
        # Дополнительные надбавки для молодых специалистов (10%)
        young_specialist_bonus = Decimal('0.0')
        if teacher.get('is_young_specialist', False):
            young_specialist_bonus = base_salary * Decimal('0.1')
        
        # Учет больничных (80% от ставки)
        sick_leave_pay = Decimal('0.0')
        if sick_leave_hours > 0:
            sick_leave_pay = sick_leave_hours * hourly_rate * Decimal('0.8')
        
        # Расчет отпускных
        vacation_days = self._get_vacation_days(teacher)
        # В данной реализации просто запоминаем количество дней отпуска
        # Расчет отпускных производится отдельно при взятии отпуска
        vacation_pay = Decimal(str(calc_data.get('vacation_pay', 0)))
        
        # Расчет валовой (до налогообложения) и чистой (после налогов) зарплаты
        gross_salary = (base_salary + position_bonus + degree_bonus + 
                      experience_bonus + category_bonus + 
                      young_specialist_bonus + sick_leave_pay + bonus)
        
        # Расчет налога
        tax_amount = (gross_salary * tax_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет профсоюзных взносов (1% для членов профсоюза)
        union_contribution = Decimal('0.0')
        if teacher.get('is_union_member', False):
            union_contribution = (gross_salary * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Чистая зарплата после вычета налогов и взносов
        net_salary = gross_salary - tax_amount - union_contribution
        
        # Округляем все денежные значения до 2 знаков после запятой
        def round_decimal(value):
            return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        base_salary = round_decimal(base_salary)
        position_bonus = round_decimal(position_bonus)
        degree_bonus = round_decimal(degree_bonus)
        experience_bonus = round_decimal(experience_bonus)
        category_bonus = round_decimal(category_bonus)
        young_specialist_bonus = round_decimal(young_specialist_bonus)
        sick_leave_pay = round_decimal(sick_leave_pay)
        gross_salary = round_decimal(gross_salary)
        net_salary = round_decimal(net_salary)
        
        # Подготовка результата расчета
        calculation_result = {
            'teacher_id': teacher_id,
            'teacher_name': teacher['name'],
            'calculation_date': calculation_date,
            'hours_worked': float(hours_worked),
            'sick_leave_hours': float(sick_leave_hours),
            'absence_hours': float(absence_hours),
            'hourly_rate': float(hourly_rate),
            'base_salary': float(base_salary),
            'bonus': float(bonus),
            'tax_rate': float(tax_rate),
            'gross_salary': float(gross_salary),
            'net_salary': float(net_salary),
            'vacation_days': vacation_days,
            'vacation_pay': float(vacation_pay),
            'position_bonus': float(position_bonus),
            'degree_bonus': float(degree_bonus),
            'experience_bonus': float(experience_bonus),
            'category_bonus': float(category_bonus),
            'young_specialist_bonus': float(young_specialist_bonus),
            'sick_leave_pay': float(sick_leave_pay),
            'union_contribution': float(union_contribution),
            'tax_amount': float(tax_amount)
        }
        
        logger.info(f"Выполнен расчет зарплаты для преподавателя {teacher['name']} (ID: {teacher_id})")
        return calculation_result
    
    def save_calculation(self, calculation_data: Dict[str, Any]) -> int:
        """
        Сохранить расчет зарплаты в базу данных
        
        :param calculation_data: данные расчета
        :return: ID сохраненного расчета
        """
        # Фильтруем и преобразуем данные для соответствия структуре таблицы
        db_calculation_data = {
            'teacher_id': calculation_data['teacher_id'],
            'calculation_date': calculation_data['calculation_date'],
            'hours_worked': calculation_data['hours_worked'],
            'sick_leave_hours': calculation_data['sick_leave_hours'],
            'absence_hours': calculation_data['absence_hours'],
            'bonus': calculation_data['bonus'],
            'tax_rate': calculation_data['tax_rate'],
            'gross_salary': calculation_data['gross_salary'],
            'net_salary': calculation_data['net_salary'],
            'vacation_days': calculation_data['vacation_days'],
            'vacation_pay': calculation_data['vacation_pay'],
            'position_bonus': calculation_data['position_bonus'],
            'degree_bonus': calculation_data['degree_bonus'],
            'experience_bonus': calculation_data['experience_bonus'],
            'category_bonus': calculation_data['category_bonus']
        }
        
        # Сохраняем расчет в базу данных
        calculation_id = self.salary_repo.add_calculation(db_calculation_data)
        logger.info(f"Расчет зарплаты сохранен в базу данных с ID: {calculation_id}")
        return calculation_id

    def calculate_vacation_pay(self, teacher_id: int, start_date: datetime.date, 
                            end_date: datetime.date) -> Dict[str, Any]:
        """
        Расчет отпускных
        
        :param teacher_id: ID преподавателя
        :param start_date: дата начала отпуска
        :param end_date: дата окончания отпуска
        :return: информация о расчете отпускных
        """
        # Получение данных преподавателя
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        # Расчет количества дней отпуска
        vacation_days = (end_date - start_date).days + 1
        max_vacation_days = self._get_vacation_days(teacher)
        
        if vacation_days > max_vacation_days:
            logger.warning(f"Запрошено больше дней отпуска ({vacation_days}), чем положено ({max_vacation_days})")
        
        # Получаем все расчеты зарплаты за последние 12 месяцев
        year_ago = start_date - datetime.timedelta(days=365)
        calculations = self.salary_repo.get_calculations_by_teacher_and_period(
            teacher_id, year_ago, start_date)
        
        if not calculations:
            raise ValueError("Нет данных о зарплате за последние 12 месяцев для расчета отпускных")
        
        # Рассчитываем среднюю дневную зарплату
        total_gross = sum(Decimal(str(calc['gross_salary'])) for calc in calculations)
        
        # Подсчет рабочих дней (без выходных)
        working_days = 0
        current_date = year_ago
        while current_date <= start_date:
            # Если день не является выходным (суббота или воскресенье)
            if current_date.weekday() < 5:
                working_days += 1
            current_date += datetime.timedelta(days=1)
        
        # Если нет рабочих дней, используем стандартное количество (250 рабочих дней в году)
        working_days = working_days if working_days > 0 else 250
        
        avg_daily_salary = (total_gross / Decimal(str(working_days))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет отпускных
        vacation_pay = (avg_daily_salary * Decimal(str(vacation_days))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет налога с отпускных
        tax_rate = self.standard_tax_rate
        tax_amount = (vacation_pay * tax_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет профсоюзных взносов с отпускных
        union_contribution = Decimal('0.0')
        if teacher.get('is_union_member', False):
            union_contribution = (vacation_pay * Decimal('0.01')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Чистая сумма отпускных
        net_vacation_pay = vacation_pay - tax_amount - union_contribution
        
        # Результат расчета
        result = {
            'teacher_id': teacher_id,
            'teacher_name': teacher['name'],
            'start_date': start_date,
            'end_date': end_date,
            'vacation_days': vacation_days,
            'avg_daily_salary': float(avg_daily_salary),
            'gross_vacation_pay': float(vacation_pay),
            'tax_amount': float(tax_amount),
            'union_contribution': float(union_contribution),
            'net_vacation_pay': float(net_vacation_pay)
        }
        
        logger.info(f"Рассчитаны отпускные для преподавателя {teacher['name']} (ID: {teacher_id})")
        return result

    def calculate_sick_leave(self, teacher_id: int, start_date: datetime.date,
                           end_date: datetime.date, is_work_related: bool = False) -> Dict[str, Any]:
        """
        Расчет больничных
        
        :param teacher_id: ID преподавателя
        :param start_date: дата начала больничного
        :param end_date: дата окончания больничного
        :param is_work_related: связан ли больничный с производственной травмой
        :return: информация о расчете больничных
        """
        # Получение данных преподавателя
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        # Расчет количества дней больничного
        sick_days = (end_date - start_date).days + 1
        
        # Получаем все расчеты зарплаты за последние 6 месяцев
        six_months_ago = start_date - datetime.timedelta(days=180)
        calculations = self.salary_repo.get_calculations_by_teacher_and_period(
            teacher_id, six_months_ago, start_date)
        
        if not calculations:
            raise ValueError("Нет данных о зарплате за последние 6 месяцев для р��счета больничных")
        
        # Рассчитываем среднюю дневную зарплату
        total_gross = sum(Decimal(str(calc['gross_salary'])) for calc in calculations)
        working_days = sum(1 for _ in range((start_date - six_months_ago).days + 1) 
                          if not (_.weekday() >= 5))  # не считаем выходные
        
        # Если нет рабочих дней, используем стандартное количество (126 рабочих дней в полугодии)
        working_days = working_days if working_days > 0 else 126
        
        avg_daily_salary = (total_gross / Decimal(str(working_days))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Определяем процент оплаты в зависимости от стажа и типа больничного
        payment_percentage = self._get_sick_leave_percentage(teacher, is_work_related)
        
        # Расчет оплаты больничного
        sick_leave_pay = (avg_daily_salary * Decimal(str(sick_days)) * 
                         (payment_percentage / Decimal('100.0'))).quantize(
                             Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет налога с больничных
        tax_rate = self.standard_tax_rate
        tax_amount = (sick_leave_pay * tax_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Расчет профсоюзных взносов с больничных
        union_contribution = Decimal('0.0')
        if teacher.get('is_union_member', False):
            union_contribution = (sick_leave_pay * Decimal('0.01')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Чистая сумма больничных
        net_sick_leave_pay = sick_leave_pay - tax_amount - union_contribution
        
        # Результат расчета
        result = {
            'teacher_id': teacher_id,
            'teacher_name': teacher['name'],
            'start_date': start_date,
            'end_date': end_date,
            'sick_days': sick_days,
            'avg_daily_salary': float(avg_daily_salary),
            'payment_percentage': float(payment_percentage),
            'gross_sick_leave_pay': float(sick_leave_pay),
            'tax_amount': float(tax_amount),
            'union_contribution': float(union_contribution),
            'net_sick_leave_pay': float(net_sick_leave_pay),
            'is_work_related': is_work_related
        }
        
        logger.info(f"Рассчитаны больничные для преподавателя {teacher['name']} (ID: {teacher_id})")
        return result
    
    def _get_sick_leave_percentage(self, teacher: Dict[str, Any], is_work_related: bool) -> Decimal:
        """
        Определение процента оплаты больничного
        
        :param teacher: данные преподавателя
        :param is_work_related: связан ли больничный с производственной травмой
        :return: процент оплаты
        """
        # Если больничный связан с производственной травмой - 100%
        if is_work_related:
            return Decimal('100.0')
        
        # Для молодых специалис��ов - 85%
        if teacher.get('is_young_specialist', False):
            return Decimal('85.0')
        
        # В зависимости от стажа
        experience_years = teacher.get('experience_years', 0)
        
        if experience_years < 5:
            return Decimal('80.0')  # менее 5 лет стажа - 80%
        elif experience_years < 8:
            return Decimal('85.0')  # от 5 до 8 лет - 85%
        elif experience_years < 15:
            return Decimal('90.0')  # от 8 до 15 лет - 90%
        else:
            return Decimal('100.0')  # свыше 15 лет - 100%

    def get_teacher_statistics(self, teacher_id: int, year: int) -> Dict[str, Any]:
        """
        Получить статистику по зарплате преподавателя за год
        
        :param teacher_id: ID преподавателя
        :param year: год для анализа
        :return: статистика по зарплате
        """
        # Получение данных преподавателя
        teacher = self.teacher_repo.get_teacher_by_id(teacher_id)
        if not teacher:
            raise ValueError(f"Преподаватель с ID {teacher_id} не найден")
        
        # Определяем период
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)
        
        # Получаем все расчеты зарплаты за указанный год
        calculations = self.salary_repo.get_calculations_by_teacher_and_period(
            teacher_id, start_date, end_date)
        
        if not calculations:
            return {
                'teacher_id': teacher_id,
                'teacher_name': teacher['name'],
                'year': year,
                'total_gross': 0.0,
                'total_net': 0.0,
                'total_tax': 0.0,
                'avg_monthly_gross': 0.0,
                'avg_monthly_net': 0.0,
                'total_vacation_pay': 0.0,
                'total_sick_leave_pay': 0.0,
                'months_data': []
            }
        
        # Группируем данные по месяцам
        months_data = {}
        for calc in calculations:
            month = calc['calculation_date'].month
            if month not in months_data:
                months_data[month] = {
                    'month': month,
                    'month_name': self._get_month_name(month),
                    'gross_salary': 0.0,
                    'net_salary': 0.0,
                    'tax_amount': 0.0,
                    'vacation_pay': 0.0,
                    'sick_leave_pay': 0.0,
                    'hours_worked': 0
                }
            
            # Суммируем данные
            months_data[month]['gross_salary'] += calc['gross_salary']
            months_data[month]['net_salary'] += calc['net_salary']
            months_data[month]['tax_amount'] += (calc['gross_salary'] * calc['tax_rate'])
            months_data[month]['vacation_pay'] += calc['vacation_pay']
            months_data[month]['sick_leave_pay'] += (calc['sick_leave_hours'] * calc['hourly_rate'] * 0.8)
            months_data[month]['hours_worked'] += calc['hours_worked']
        
        # Преобразуем данные в список и сортируем по месяцам
        months_list = [data for _, data in sorted(months_data.items())]
        
        # Рассчитываем общие суммы
        total_gross = sum(data['gross_salary'] for data in months_list)
        total_net = sum(data['net_salary'] for data in months_list)
        total_tax = sum(data['tax_amount'] for data in months_list)
        total_vacation_pay = sum(data['vacation_pay'] for data in months_list)
        total_sick_leave_pay = sum(data['sick_leave_pay'] for data in months_list)
        
        # Среднемесячные значения
        months_count = len(months_list)
        avg_monthly_gross = total_gross / months_count if months_count > 0 else 0
        avg_monthly_net = total_net / months_count if months_count > 0 else 0
        
        # Итоговая статистика
        result = {
            'teacher_id': teacher_id,
            'teacher_name': teacher['name'],
            'year': year,
            'total_gross': float(total_gross),
            'total_net': float(total_net),
            'total_tax': float(total_tax),
            'avg_monthly_gross': float(avg_monthly_gross),
            'avg_monthly_net': float(avg_monthly_net),
            'total_vacation_pay': float(total_vacation_pay),
            'total_sick_leave_pay': float(total_sick_leave_pay),
            'months_data': months_list
        }
        
        logger.info(f"Сформирована статистика за {year} год для преподавателя {teacher['name']} (ID: {teacher_id})")
        return result
    
    def _get_month_name(self, month_number: int) -> str:
        """
        Получить название месяца на русском языке
        
        :param month_number: номер месяца (1-12)
        :return: название месяца
        """
        month_names = {
            1: 'Январь',
            2: 'Февраль',
            3: 'Март',
            4: 'Апрель',
            5: 'Май',
            6: 'Июнь',
            7: 'Июль',
            8: 'Август',
            9: 'Сентябрь',
            10: 'Октябрь',
            11: 'Ноябрь',
            12: 'Декабрь'
        }
        return month_names.get(month_number, f"Месяц {month_number}")