from flask import jsonify
from wikked.scm.base import SourceControlError
from wikked.web import app
from wikked.webimpl import PermissionError


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


@app.errorhandler(PermissionError)
def handle_permission_error(error):
    app.log_exception(error)
    resp = {
            'error': {
                'type': 'permission',
                'message': str(error)
                }
            }
    return jsonify(resp), 403

