import calendar
import os
import random
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from flask import Flask

from .config import Email, WeekConfig
from .models import db


def look_column(
        data_f: pd.DataFrame,
        dict_days: List[int],
        off_days: List[List[int]],
        start_weekday: int,
        weekly_plan: Dict[str, int]
) -> pd.DataFrame:
    """
    Adjusts the schedule based on worker availability, weekly plans, and required workers.

    Args:
        data_f (pd.DataFrame): A DataFrame representing the schedule grid.
        dict_days (List[int]): A list where each element represents the total number of days off for a worker.
        off_days (List[List[int]]): A list of lists where each sublist contains the specific days a worker is unavailable.
        start_weekday (int): The starting day of the week (0 = Monday, 6 = Sunday).
        weekly_plan (Dict[str, int]): A dictionary mapping weekdays to the required number of workers.

    Returns:
        pd.DataFrame: The modified schedule grid.
    """
    for day in range(data_f.shape[1]):
        weekday_index = (day + start_weekday) % 7
        weekday_key = WeekConfig.WEEKDAYS[weekday_index]
        required_workers = weekly_plan[weekday_key]

        workers = list(range(data_f.shape[0]))
        random.shuffle(workers)

        for worker_index in range(data_f.shape[0]):
            if day + 1 in off_days[worker_index]:
                data_f.iloc[worker_index, day] = ""
                if worker_index in workers:
                    workers.remove(worker_index)

        for worker_index in workers[:]:
            prev_days = data_f.iloc[worker_index, max(0, day - 5):day]
            if prev_days.tolist().count("X") >= 5:
                data_f.iloc[worker_index, day] = ""
                workers.remove(worker_index)

        if required_workers > 0:
            available_workers = workers[:required_workers]
            for worker_index in available_workers:
                data_f.iloc[worker_index, day] = "X"

            for worker_index in workers[required_workers:]:
                data_f.iloc[worker_index, day] = ""

        workers_working = [
            i for i in range(data_f.shape[0]) if data_f.iloc[i, day] == "X"
        ]
        if len(workers_working) < required_workers:
            additional_workers_needed = required_workers - len(workers_working)
            available_workers = [
                i for i in workers if i not in workers_working
            ]
            random.shuffle(available_workers)
            for i in available_workers[:additional_workers_needed]:
                data_f.iloc[i, day] = "X"

    for worker_index in range(data_f.shape[0]):
        total_days_off = dict_days[worker_index]
        current_days_off = data_f.iloc[
            worker_index
        ].apply(lambda x: x == "").sum()

        if current_days_off < total_days_off:
            days_to_off = total_days_off - current_days_off
            working_days = [
                day for day in range(
                    data_f.shape[1]
                ) if data_f.iloc[worker_index, day] == "X"
            ]
            random.shuffle(working_days)
            for day in working_days[:days_to_off]:
                data_f.iloc[worker_index, day] = ""

        elif current_days_off > total_days_off:
            excess_days_off = current_days_off - total_days_off
            off_days_list = [
                day for day in range(
                    data_f.shape[1]
                ) if data_f.iloc[worker_index, day] == ""
            ]
            random.shuffle(off_days_list)
            for day in off_days_list[:excess_days_off]:
                data_f.iloc[worker_index, day] = "X"

    return data_f


def generate_calendar_labels(
        days_in_month: int,
        start_weekday: int
) -> List[str]:
    """
    Generates calendar labels for a given month.

    Args:
        days_in_month (int): The number of days in the month.
        start_weekday (int): The weekday of the first day of the month (0 = Monday, 6 = Sunday).

    Returns:
        List[str]: A list of formatted labels for each day of the month.
    """
    weekdays_eng = list(WeekConfig.WEEKDAYS.values())
    labels = [
        f"[{day + 1}|{weekdays_eng[(start_weekday + day) % 7]}]" for day in range(
            days_in_month
        )
    ]
    return labels


def extract_off_days(
        data: List[Dict[str, Any]]
) -> List[List[int]]:
    """
    Extracts the list of days off for each worker.

    Args:
        data (List[Dict[str, Any]]): A list of worker data dictionaries.

    Returns:
        List[List[int]]: A list of lists where each sublist contains the days off for a worker.
    """
    off_days = []
    for worker in data[1:-1]:
        personal_days = list(
            map(int, worker['personal'].split(','))
        ) if 'personal' in worker else []
        off_days.append(personal_days)
    return off_days


def extract_dict_days(
        data: List[Dict[str, Any]]
) -> List[int]:
    """
    Extracts the total number of days off for each worker.

    Args:
        data (List[Dict[str, Any]]): A list of worker data dictionaries.

    Returns:
        List[int]: A list of total days off for each worker.
    """
    return [worker['days'] for worker in data[1:-1] if 'days' in worker]


def extract_weekly_plan(
        data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Extracts the weekly plan from the data.

    Args:
        data (List[Dict[str, Any]]): A list of worker data dictionaries.

    Returns:
        Dict[str, int]: A dictionary mapping weekdays to the required number of workers.
    """
    week_string = data[-1]['week']
    week_values = list(map(int, eval(week_string)))
    weekdays_keys = list(WeekConfig.WEEKDAYS.values())
    return dict(zip(weekdays_keys, week_values))


def validate_schedule_with_question_marks(
        data_f: pd.DataFrame,
        weekly_plan: Dict[str, int],
        start_weekday: int
) -> pd.DataFrame:
    """
    Validates the schedule and fills missing worker slots with question marks.

    Args:
        data_f (pd.DataFrame): The schedule grid.
        weekly_plan (Dict[str, int]): The weekly plan with required workers per day.
        start_weekday (int): The starting weekday of the schedule.

    Returns:
        pd.DataFrame: The validated schedule grid.
    """
    for day in range(data_f.shape[1]):
        weekday_index = (day + start_weekday) % 7
        weekday_key = WeekConfig.WEEKDAYS[weekday_index]
        required_workers = weekly_plan[weekday_key]

        workers_present = data_f.iloc[:, day].apply(lambda x: x == "X").sum()

        if workers_present < required_workers:
            for worker_index in range(data_f.shape[0]):
                if data_f.iloc[worker_index, day] != "X":
                    data_f.iloc[worker_index, day] = "?"

    return data_f


def process_data(
        data: List[Dict[str, Any]],
        user_id: str
) -> pd.DataFrame:
    """
    Processes the input data and generates a schedule.

    Args:
        data (List[Dict[str, Any]]): Input data containing worker information and scheduling rules.
        user_id (str): The user ID for whom the schedule is generated.

    Returns:
        pd.DataFrame: The final schedule as a DataFrame.
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month + 1 if now.month < 12 else 1
    if current_month == 1:
        current_year += 1
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    start_weekday = calendar.monthrange(current_year, current_month)[0]

    column_names = generate_calendar_labels(days_in_month, start_weekday)

    index_names = [worker['name'] for worker in data[1:-1] if 'name' in worker]

    df = pd.DataFrame(index=index_names, columns=column_names)

    dict_days = extract_dict_days(data)
    off_days = extract_off_days(data)
    weekly_plan = extract_weekly_plan(data)

    df = look_column(df, dict_days, off_days, start_weekday, weekly_plan)
    df = validate_schedule_with_question_marks(df, weekly_plan, start_weekday)

    creator_info = data[0]
    creator = creator_info['creator']
    firm_name = creator_info['firm_name']
    creator_series = pd.Series(
        [
            f'Creator: {creator}', f'Company: {firm_name}'
        ] + [''] * (df.shape[1] - 2),
        index=df.columns
    )
    creator_df = pd.DataFrame([creator_series], index=['Data'])
    df = pd.concat([df, creator_df])

    os.makedirs('schedule', exist_ok=True)
    csv_path = os.path.join('schedule', f'{user_id}.csv')
    df.to_csv(csv_path, index=True)

    excel_path = os.path.join('schedule', f'{user_id}.xlsx')
    df.to_excel(excel_path)

    return df


def data_readable(
        data_list: List[Any]
) -> List[Dict[str, Any]]:
    """
    Converts SQLAlchemy objects into readable dictionaries.

    Args:
        data_list (List[Any]): A list of SQLAlchemy objects.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries with SQLAlchemy metadata excluded.
    """
    new_list = []
    for items in data_list:
        new_list.extend([
            {key: value for key, value in entry.__dict__.items() if key != '_sa_instance_state'}
            for entry in items
        ])
    return new_list


def search_folder(
        user_id: str,
        file_type: str
) -> str:
    """
    Constructs the file path for a user's schedule based on their user ID and file type.

    Args:
        user_id (str): The unique ID of the user.
        file_type (str): The type of file (e.g., 'csv', 'xlsx').

    Returns:
        str: The full path to the user's schedule file.
    """
    project_root = os.getcwd()
    schedule_folder = os.path.join(project_root, "schedule")
    file_path = os.path.join(schedule_folder, f"{user_id}.{file_type}")
    return file_path


def send_email(
        email: str,
        data: str
) -> None:
    """
    Sends an email with an attached file.

    Args:
        email (str): The recipient's email address.
        data (str): The path to the file to be attached.

    Returns:
        None
    """
    gmail_user = Email.LOGIN
    gmail_password = Email.PASSWORD

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = email
    msg['Subject'] = Email.DATA_SUBJECT

    attachment = MIMEBase('application', 'octet-stream')
    with open(data, 'rb') as file:
        attachment.set_payload(file.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        'Content-Disposition', f'attachment; filename="{Path(data).name}"'
    )
    msg.attach(attachment)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, email, msg.as_string())


def create_database_structure(
        app: Flask
) -> None:
    """
    Creates the database tables based on the defined models in the Flask application.

    Args:
        app (Flask): The Flask application instance.

    Returns:
        None
    """
    with app.app_context():
        db.create_all()
