from flask import render_template


from flask import request, jsonify
import os
from flask import Blueprint
from fitlog.fastserver.server.data_container import all_data, all_handlers, handler_watcher
from fitlog.fastlog.log_read import is_log_dir_has_step, is_log_record_finish
from fitlog.fastserver.server.chart_utils import ChartStepLogHandler

import uuid

chart_page = Blueprint("chart_page", __name__, template_folder='templates')

@chart_page.route('/chart', methods=['POST'])
def chart():
    if all_data['debug']:
        log_dir = ''  # 如果是debug，在这里设置log dir
    else:
        log_dir = request.values['log_dir']
    finish = request.values['finish']
    save_log_dir = os.path.join(all_data['root_log_dir'], log_dir)
    chart_exclude_columns = all_data['chart_settings']['chart_exclude_columns']
    _uuid = str(uuid.uuid1())
    max_points = all_data['chart_settings']['max_points']
    handler = ChartStepLogHandler(save_log_dir, _uuid, round_to=all_data['basic_settings']['round_to'],
                            max_steps=max_points,
                            wait_seconds=all_data['chart_settings']['wait_seconds'],
                            exclude_columns=chart_exclude_columns)
    only_once = is_log_record_finish(save_log_dir) or finish=='true'
    points = handler.update_logs(only_once) # {'loss': [{}, {}], 'metric':[{}, {}]}
    if not only_once:
        all_handlers[_uuid] = handler
        if not handler_watcher._start:
            handler_watcher.start()

    return render_template('chart.html', log_dir=log_dir, data=points, chart_uuid=_uuid, max_steps=max_points,
                           server_uuid=all_data['uuid'],
                           update_every=all_data['chart_settings']['update_every']*1000)

@chart_page.route('/chart/new_step', methods=['POST'])
def chart_new_step():
    # 获取某个log_dir的更新
    _uuid = request.json['chart_uuid']

    points = {}
    if _uuid in all_handlers:
        handler = all_handlers[_uuid]
        points = handler.update_logs()
    else:
        points['finish'] = True

    return jsonify(steps=points)

@chart_page.route('/chart/have_trends', methods=['POST'])
def have_trends():
    try:
        log_dir = request.json['log_dir']
        save_log_dir = os.path.join(all_data['root_log_dir'], log_dir)
        if is_log_dir_has_step(save_log_dir):
            return jsonify(status='success', have_trends=True)
        else:
            return jsonify(status='success', have_trends=False)
    except Exception:
        print("Exception detected in have_trends(")
        return jsonify(status='fail', have_trends=False)
