from flask import request, jsonify, render_template
from wikked.scm.base import SourceControlError
from wikked.views import add_auth_data, add_navigation_data
from wikked.web import app
from wikked.webimpl import UserPermissionError


def _render_error(error=None, error_details=None, tpl_name=None):
    if error is not None:
        error = str(error)

    data = {}
    if error:
        data['error'] = error
    if error_details:
        data['error_details'] = error_details

    add_auth_data(data)
    add_navigation_data(None, data)
    tpl_name = tpl_name or 'error.html'
    return render_template(tpl_name, **data)


def _jsonify_error(error_type='error', error=None, error_details=None,
                   error_code=500):
    resp = {
            'error': {
                'type': error_type,
                'message': error
                }
            }
    if error_details:
        resp['error'].update(error_details)
    return jsonify(resp), error_code


@app.errorhandler(SourceControlError)
def handle_source_control_error(error):
    app.log_exception(error)
    if request.path.startswith('/api/'):
        return _jsonify_error('source_control',
                              error.message,
                              {'operation': error.operation})
    else:
        return _render_error("Source Control Error", error.message)


@app.errorhandler(UserPermissionError)
def handle_permission_error(error):
    if request.path.startswith('/api/'):
        return _jsonify_error('user_permission',
                              str(error))
    else:
        perms = error.perm
        tpl_name = 'error-unauthorized.html'
        if 'edit' in perms or 'create' in perms:
            tpl_name = 'error-unauthorized-edit.html'
        elif 'upload' in perms:
            tpl_name = 'error-unauthorized-upload.html'
        return _render_error("User Permission Error", str(error), tpl_name)
