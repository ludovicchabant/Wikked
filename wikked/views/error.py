from flask import jsonify
from wikked.scm.base import SourceControlError
from wikked.web import app


@app.errorhandler(SourceControlError)
def handle_source_control_error(error):
    app.log_exception(error)
    resp = {
            'error': {
                'type': 'source_control',
                'operation': error.operation,
                'message': error.message
                }
            }
    return jsonify(resp), 500

