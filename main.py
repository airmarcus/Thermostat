import traceback

from flask import Flask, render_template, jsonify, request, redirect, make_response
import requests
from datetime import datetime, timedelta
import threading
import time
import pandas


app = Flask(__name__)
tstat1_url = "http://192.168.1.147/tstat"
tstat2_url = "http://192.168.1.61/tstat"

@app.route("/")
def hello():
    print("Connecting")
    tstat_data = requests.get(tstat1_url)
    tstat2 = requests.get(tstat2_url)
    tstat_dict = tstat_data.json()
    tstat2_dict = tstat2.json()
    df = pandas.read_csv('fan_record.csv')
    tstat_dict['minutes'] = get_last_day(df[df['tstat'] == 1])
    tstat2_dict['minutes'] = get_last_day(df[df['tstat'] == 2])
    return render_template('index.html', tstat1=tstat_dict, tstat2=tstat2_dict)


def get_last_day(df):
    pandas.set_option('mode.chained_assignment', None)
    df['date'] = pandas.to_datetime(df['date'])
    current_date = datetime.now()
    past_day = current_date - timedelta(days=1)
    filtered_df = df[(df['date'] >= past_day) & (df['on'] == 1)]
    return len(filtered_df) * 2


@app.route("/newhold", methods=['POST'])
def set_hold():
    new_sp1 = request.form['setpoint1']
    new_sp2 = request.form['setpoint2']
    if new_sp1 != '':
        r = requests.post(tstat1_url, json={"t_cool": int(new_sp1), "hold": 1})
    if new_sp2 != '':
        r = requests.post(tstat2_url, json={"t_cool": int(new_sp2), "hold": 1})

    print('setting at ', new_sp1, ' and ', new_sp2)
    return make_response(redirect('/'))


def time_program(current_sp):
    programs = [{}, {21: 81, 7: 78}]
    current_hour = datetime.now().hour
    for t in range(0, len(programs)):
        for hour, temp in programs[t].items():
            if hour == current_hour and current_sp[t] != temp:
                tstat_url = tstat1_url if t == 0 else tstat2_url
                requests.post(tstat_url, json={"t_cool": temp, "hold": 1})
                print("changing it to ", temp, "per program instructions")


def record_fan():
    while True:
        try:
            set_points = []
            for i in range(0, 2):
                g_url = tstat1_url if i == 0 else tstat2_url
                try:
                    tstat = requests.get(g_url)
                except:
                    pass
                tstat = tstat.json()
                fstate = tstat['fstate']
                current_datetime = datetime.now()
                record_date = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
                data_to_write = f"{i+1},{record_date},{fstate}\n"
                file_path = "fan_record.csv"
                with open(file_path, "a") as file:
                    file.write(data_to_write)
                set_points.append(int(tstat['t_cool']))
            time_program(set_points)
            time.sleep(120)

        except Exception as e:
            print(traceback.format_exc())

fan_thread = threading.Thread(target=record_fan)
fan_thread.start()

if __name__== '__main__':
    app.run(host='0.0.0.0', port=5015)
