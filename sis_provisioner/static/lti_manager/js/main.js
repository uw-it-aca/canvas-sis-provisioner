/*jslint browser: true, plusplus: true, regexp: true */
/*global $, jQuery, Handlebars, moment, LTIConfig, confirm */

(function ($) {
    "use strict";

    $.ajaxSetup({
        headers: { "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() }
    });

    Handlebars.registerHelper('stringify', function (object) {
        return new Handlebars.SafeString(JSON.stringify(object, null, 4));
    });

    Handlebars.registerHelper('format_date', function (dt) {
        return (dt !== null) ? moment(dt).format('MM/DD/YYYY h:mm a') : '';
    });

    function draw_error(xhr) {
        var json;
        try {
            json = $.parseJSON(xhr.responseText);
            $('.et-errors').html(json.error);
            $('#et-alert').show();
        } catch (e) {
            console.log('Unknown admin service error');
        }
    }

    function draw_updated_tool() {
        $('#external-tool-editor').modal('hide');
        load_external_tools();
    }

    function gather_form_data() {
        var data = {
            'canvas_id': $('#et-id-input').val(),
            'config': $.parseJSON($('#et-config-input').val()),
            'account_id': $('#et-account-input').val()
        };
        return {'external_tool': data};
    }

    function save_external_tool() {
        var json_data = gather_form_data(),
            tool_id = json_data.external_tool.canvas_id,
            url = 'lti_manager/api/v1/external_tool/',
            type = 'POST';

        if (tool_id.length) {
            url += tool_id;
            type = 'PUT';
        }

        $.ajax({
            url: url,
            type: type,
            dataType: 'json',
            data: JSON.stringify(json_data)
        }).done(draw_updated_tool).fail(draw_error);
    }

    function load_external_tool(tool_id, done_fn) {
        $.ajax({
            url: 'lti_manager/api/v1/external_tool/' + tool_id,
            type: 'GET',
            dataType: 'json'
        }).done(done_fn).fail(draw_error);
    }

    function delete_external_tool() {
        /*jshint validthis: true */
        var tool_id = $(this).attr('data-tool-id');
        if (confirm('Really delete this external tool?')) {
            $.ajax({
                url: 'lti_manager/api/v1/external_tool/' + tool_id,
                type: 'DELETE',
                dataType: 'json'
            }).done(draw_updated_tool).fail(draw_error);
        }
    }

    function open_editor(title) {
        $('#et-modal-title').html(title);
        $('#et-alert').hide();
        $('#external-tool-editor').modal({
            backdrop: 'static',
            show: true
        });
    }

    function update_textarea(json) {
        $('#et-config-input').val(JSON.stringify(json));
    }

    function prepare_json(source) {
        var json = $.extend(true, {}, LTIConfig);
        if (source === null) {
            return json;
        }
        return $.extend(true, json, source);
    }

    function load_form_data(data) {
        var json = prepare_json(data.external_tool.config);

        $('#et-id-input').val(data.external_tool.canvas_id);
        $('#et-account-input').val(data.external_tool.account_id);
        if (data.external_tool.canvas_id && data.external_tool.account_id) {
            $('#et-account-input').prop('disabled', true);
        } else {
            $('#et-account-input').prop('disabled', false);
        }
        update_textarea(json);
        $('#et-json-editor').jsonEditor(json, {
            change: update_textarea
        });
    }

    function load_add_external_tool() {
        open_editor('Add an External Tool');
        load_form_data({'external_tool': {
            'id': null,
            'account_id': null,
            'config': null
        }});
    }

    function load_clone_external_tool() {
        /*jshint validthis: true */
        var tool_id = $(this).attr('data-tool-id');
        open_editor('Clone an External Tool');
        load_external_tool(tool_id, function (data) {
            data.external_tool.canvas_id = '';
            data.external_tool.config.id = '';
            load_form_data(data);
        });
    }

    function load_edit_external_tool() {
        /*jshint validthis: true */
        var tool_id = $(this).attr('data-tool-id');
        open_editor('Edit an External Tool');
        load_external_tool(tool_id, load_form_data);
    }

    function draw_external_tools(data) {
        var tpl = Handlebars.compile($('#tool-table-row').html());

        if ($.fn.dataTable.isDataTable('#external-tools-table')) {
            $('#external-tools-table').DataTable().destroy();
        }

        $('#external-tools-table tbody').html(tpl(data));
        $('#external-tools-table').DataTable({
            'aaSorting': [[ 0, 'asc' ]],
            'bPaginate': false,
            'searching': false,
            'bScrollCollapse': true
        });

        $('.et-add').click(load_add_external_tool);
        $('.et-edit').click(load_edit_external_tool);
        $('.et-clone').click(load_clone_external_tool);
        $('.et-delete').click(delete_external_tool);
    }

    function load_external_tools() {
        $.ajax({
            url: 'lti_manager/api/v1/external_tools',
            type: 'GET',
            dataType: 'json'
        }).done(draw_external_tools).fail(draw_error);
    }

    function initialize() {
        load_external_tools();
        $('.save-btn').click(save_external_tool);
    }

    $(document).ready(function () {
        initialize();
    });
}(jQuery));
