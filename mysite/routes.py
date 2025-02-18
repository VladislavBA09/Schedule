import os
import uuid

import pandas as pd
from flask import Blueprint, render_template, request, session

from .models import First, Second, Third, db
from .processor import data_readable, process_data, search_folder, send_email

admin = Blueprint('admin', __name__)


@admin.route('/', methods=['GET'])
def main_page() -> str:
    """
    Renders the main page of the application.
    If the user does not have a 'user_id' in the session, it assigns one.

    Returns:
        str: The rendered HTML template for the main page.
    """
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['is_complete'] = False
    return render_template('main_page.html')


@admin.route('/first_step', methods=['GET'])
def first_step() -> str:
    """
    Renders the first step page of the application.
    If the user does not have a 'user_id' in the session, it assigns one.

    Returns:
        str: The rendered HTML template for the first step.
    """
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['is_complete'] = False
    return render_template('first_step.html')


@admin.route('/second_step', methods=['GET', 'POST'])
def second_step() -> str:
    """
    Handles the second step of the process, where user information (creator, firm name, number) is collected.
    On POST request, it saves the data to the database.

    Returns:
        str: The rendered HTML template for the second step.
    """
    if request.method == 'POST':
        name = request.form.get('creator')
        firm_name = request.form.get('firm_name')
        number = request.form.get('number')
        user_id = session.get('user_id')
        if not user_id:
            return render_template('main_page.html')

        new_entry = First(
            creator=name,
            firm_name=firm_name,
            number=number,
            user_id=user_id
        )
        db.session.add(new_entry)
        db.session.commit()

        return render_template(
            'second_step.html',
            number=int(number)
        )

    number = request.args.get('number')
    return render_template(
        'second_step.html',
        number=int(number)
    )


@admin.route('/third_step', methods=['GET', 'POST'])
def third_step() -> str:
    """
    Handles the third step where a list of names, days, and personal days is collected.
    On POST request, it saves the data to the database.

    Returns:
        str: The rendered HTML template for the third step.
    """
    if request.method == 'POST':
        names = request.form.getlist('names[]')
        days = request.form.getlist('days[]')
        personal = request.form.getlist('personal[]')
        user_id = session.get('user_id')
        if not user_id:
            return render_template('main_page.html')

        for name, day, personal in zip(names, days, personal):
            new_entry = Second(
                name=name,
                days=day,
                personal=personal,
                user_id=user_id
            )
            db.session.add(new_entry)
            db.session.commit()

        return render_template('third_step.html')

    return render_template('third_step.html')


@admin.route('/fourth_step', methods=['GET', 'POST'])
def fourth_step() -> str:
    """
    Handles the fourth step where the weekly schedule is saved, and the schedule is processed.
    On POST request, the schedule is generated and displayed as an HTML table.

    Returns:
        str: The rendered HTML template for the fourth step with the schedule table.
    """
    if request.method == 'POST':
        monday = request.form.get('monday')
        tuesday = request.form.get('tuesday')
        wednesday = request.form.get('wednesday')
        thursday = request.form.get('thursday')
        friday = request.form.get('friday')
        saturday = request.form.get('saturday')
        sunday = request.form.get('sunday')
        user_id = session.get('user_id')
        if not user_id:
            return render_template('main_page.html')

        new_list = [
            monday,
            tuesday,
            wednesday,
            thursday,
            friday,
            saturday,
            sunday
        ]
        new_entry = Third(
            week=(str(new_list)), user_id=user_id
        )
        db.session.add(new_entry)
        db.session.commit()

        first_data = First.query.filter_by(user_id=user_id).all()
        second_data = Second.query.filter_by(user_id=user_id).all()
        third_data = Third.query.filter_by(user_id=user_id).all()

        data = data_readable([first_data, second_data, third_data])
        process_data(data, user_id)
        df = pd.read_csv(search_folder(user_id, 'csv'))

        table_html = df.to_html(classes='table table-striped table-bordered')

        return render_template(
            'fourth_step.html',
            table_html=table_html
        )

    return render_template('fourth_step.html')


@admin.route('/fifth_step', methods=['POST'])
def fifth_step() -> str:
    """
    Handles the fifth step where the user can enter an email and request to send the generated schedule file.
    On POST request, the email is sent with the file as an attachment.

    Returns:
        str: The rendered HTML template for the fifth step.
    """
    user_id = session.get('user_id')
    email = request.form.get('email')
    file_type = request.form.get('fileType')
    send_file_button = request.form.get('send_file')

    if not user_id:
        return render_template('main_page.html')

    if send_file_button:
        send_email(email, search_folder(user_id, file_type))
        return render_template('main_page.html')

    return render_template(
        'fifth_step.html',
        data=[email, file_type]
    )


@admin.route('/cleanup_session', methods=['POST'])
def cleanup_session() -> str:
    """
    Cleans up the session by deleting the user's data from the database and removing any associated files.

    Returns:
        str: An empty string with a status code of 204 (No Content) if successful.
        If an error occurs, it returns a 500 status code with an error message.
    """
    user_id = session.get('user_id')
    if not user_id:
        return '', 204

    try:
        db.session.query(First).filter_by(user_id=user_id).delete()
        db.session.query(Second).filter_by(user_id=user_id).delete()
        db.session.query(Third).filter_by(user_id=user_id).delete()
        db.session.commit()

        file_paths = [
            os.path.join('schedule', f'{user_id}.csv'),
            os.path.join('schedule', f'{user_id}.xlsx')
        ]
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)

        session.pop('user_id', None)

        return '', 204
    except Exception as e:
        db.session.rollback()
        print(f"Error clean data: {e}")
        return '', 500
