/* canvas course group javascript */

$(document).ready(function() {

    if (window.course_groups.hasOwnProperty('validation_error')) {
        return;
    }

    // prep for api post/put
    var csrfSafeMethod = function(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    };

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (window.course_groups.session_id) {
                xhr.setRequestHeader("X-SessionId", window.course_groups.session_id);
            }
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", window.course_groups.csrftoken);
            }
        }
    });

    var groupDataFromJSON = function (group) {
        var when,
            is_provisioned,
            in_process = false;

        if (group.provisioned_date && group.provisioned_date.length) {
            is_provisioned = true;
            when = group.provisioned_date;
        } else {
            is_provisioned = false;
            when = group.added_date;
        }

        if (group.queue_id && group.queue_id.length) {
            in_process = true;
        }

        return {
            id: group.id,
            group_id: group.group_id,
            course_id: group.course_id,
            role: group.role,
            added_by: group.added_by,
            priority: group.priority,
            when: when ? $.datepicker.formatDate('MM d, yy', new Date(when)) : null,
            is_provisioned: is_provisioned,
            in_process: in_process
        };
    };

    var newGroupInput = function () {
        var tpl = Handlebars.compile($('#new-group-item').html()),
            e = $(tpl({group_id: '', roles: window.course_groups.roles})),
            input = $('input', e),
            typeahead;

        $('select', e).change(lightSaveButton);

        input.attr('typeahead', 'off');
        typeahead = input.typeahead({
            minLength: 4,
            items: 50,
            source: function (query, process) {
                return $.get('api/v1/uw/group/',
                             {
                                 name: query
                             },
                             function (data) {
                                 var matches = [],
                                     i;

                                 for (i in data.groups) {
                                     matches.push(data.groups[i].name);
                                 }

                                 return process(matches);
                             });
            },
            updater: function (item) {
                this.$element.focus();
                return item;
            }
        });

        input.keyup(function (evt) {
            var group = tidyGroupId($(this).val()),
                l = (group.match(/^cou/) !== null) ? 17 :
                    (group.match(/^uw_/) !== null) ? 5 : 4;

            validateGroupInput.call(this, group);
            typeahead.data('typeahead').options.minLength = l;
        });

        input.focus(clearEmptyGroupName);
        input.blur(validateGroupName);

        $('div.new-group-list > ul').append(e);
        setEmptyGroupName.call(input);
    };

    var tidyGroupId = function (group_id) {
        return group_id.replace(/(^\s*)|(\s*$)/gi, "").toLowerCase();
    };

    var setEmptyGroupName = function () {
        var input = $(this),
            div = input.parent();

        if (tidyGroupId(input.val()).length < 1) {
            input.val('type or paste UW Group ID');
            div.addClass('no-value');
        }
    };

    var clearEmptyGroupName = function () {
        var input = $(this),
            div = input.parent();

        if (div.hasClass('no-value')) {
            div.removeClass('no-value');
            input.val('');
        }
    };

    var validGroupName = function (group) {
        return (group.match(/^[A-Za-z0-9\-\.\_]+$/) !== null);
    };

    var validateGroupName = function () {
        var group,
            div,
            span;

        if ($(this).next('ul.typeahead').is(":visible")) {
            return;
        }

        group = tidyGroupId($(this).val());
        div = $(this).parent();
        span = $('> span', div);

        // look like a reasonable group?
        validateGroupInput.call(this);

        if (group.length) {
            if (!div.hasClass('invalid')) {
                var me = this,
                    i;

                $.ajax({
                    type: 'GET',
                    url: 'api/v1/uw/group/' + group + '/membership',
                    async: false
                }).done(function(data) {
                    validateGroupMembers(group, data.invalid, warnBadNewGroupMembers);
                }).fail(function (xhr, textStatus, errorThrown) {
                    var errstr;

                    try {
                        if (xhr.status == 401) {
                            errstr = warnPermissionDenied();
                        } else{
                            errstr = $.parseJSON(xhr.responseText).error;
                        }
                    } catch (e) {
                        errstr = xhr.responseText;
                    }

                    setGroupInputValidity.call(me, errstr);
                });
            }
        } else {
            setEmptyGroupName.call(this);
        }
    };

    var validateGroupMembers = function (group, invalid, warning) {
        var exceptions = [],
            member,
            i;

        for (i in invalid) {
            exceptions.push({ member: invalid[i] });
        }

        if (exceptions.length) {
            return warning.call(this, group, exceptions);
        }

        return null;
    };

    var warnBadExistingGroupMembers = function (group, exceptions) {
        var tpl = Handlebars.compile($('#group-member-exceptions').html());

        return tpl({
            count: exceptions.length,
            plural: (exceptions.length > 1) ? 's' : '',
            members: exceptions
        });
    };

    var warnBadNewGroupMembers = function (group, exceptions) {
        window.course_groups.member_exceptions[group] = {
            group: group,
            count: exceptions.length,
            plural: (exceptions.length > 1) ? 's' : '',
            members: exceptions
        };
    };

    var warnPermissionDenied = function (group, exceptions) {
        var tpl = Handlebars.compile($('#permission-denied-exception').html());

        return tpl({
            group: group
        });
    };

    var validateGroupInput = function () {
        var group = tidyGroupId($(this).val());

        clearGroupInputValidity.call(this);
        if (group.length > 0) {
            if (!validGroupName(group)) {
                setGroupInputValidity.call(this, 'Invalid character in UW Group name');
            }
        }

        lightSaveButton();
    };

    var setGroupInputValidity = function (errstr) {
        var parent;

        if (errstr && errstr.length) {
            parent = $(this).parent();
            parent.addClass('invalid');
            $('> span', parent).html(errstr);
        }
    };

    var clearGroupInputValidity = function () {
        var div = $(this).parent();

        if (div.hasClass('valid') || div.hasClass('invalid') ||
                div.hasClass('warning') || div.hasClass('loading')) {
            $('> span', div).remove();
            div.removeClass('valid invalid warning loading');
            div.append('<span></span>');
        }
    };

    var lightSaveButton = function () {
        var existing = ($('div.existing-groups table tr').length > 1),
            valid = ($('div.new-group-list .invalid').length === 0),
            enable = ($('div.existing-groups .is-deleted').length > 0),
            button = $('button');

        if (enable) {
            button.prev('p').show();
        } else {
            button.prev('p').hide();
        }

        $('div.new-group-list > ul > li').each(function (i, e) {
            if (!$('div', e).hasClass('no-value') &&
                    tidyGroupId($('input', e).val()).length > 0) {
                if ($('option:selected', e).val().length > 0) {
                    enable = true;
                } else {
                    valid = false;
                }
            }
        });

        //button.html('Save ' + ((existing) ? ' changes' : 'all groups to Canvas'));
        button.html('Save');

        if (enable && valid) {
            button.removeAttr('disabled');
        } else {
            button.attr('disabled', 'disabled');
        }
    };

    var submitGroupChanges = function () {
        var failures = [];

        // add groups
        $('div.new-group-list > ul > li').each(function(i, e) {
            var group_id = $('input', e).val(),
                role = $('option:selected', e).val();

            if (role.length > 0 && group_id.length > 0) {
                $.ajax({
                    type: 'POST',
                    url: 'api/v1/group/',
                    async: false,
                    processData: false,
                    contentType: 'application/json',
                    data: '{ "course_id": "' +
                        window.course_groups.sis_course_id +
                        '", "canvas_id": "' +
                        window.course_groups.canvas_course_id +
                        '", "group_id": "' + group_id +
                        '", "role": "' + role + '" }'
                }).fail(function (xhr, textStatus, errorThrown) {
                    try {
                        failures.push($.parseJSON(xhr.responseText).error);
                    } catch (e) {
                        failures.push(xhr.responseText);
                    }
                });
            }
        });

        // delete groups
        $('div.existing-groups table tr.is-deleted').each(function(i, e) {
            $.ajax({
                type: 'DELETE',
                url: 'api/v1/group/' + $('input#group-model-id', e).val(),
                async: false
            }).fail(function (xhr, textStatus, errorThrown) {
                try {
                    failures.push($.parseJSON(xhr.responseText).error);
                } catch (e) {
                    failures.push(xhr.responseText);
                }
            });
        });

        if (failures.length > 0) {
            var bod = '<pre class="alert-error">',
                fail;

            for (fail in failures) {
                bod += failures[fail];
            }

            bod += '</pre>';

            $('#closing-failure .modal-body div').html(bod);


            $('#closing-failure').modal();

            return false;
        }

        return true;
    };

    $(window).on('beforeunload', function(){
        if ($('button').attr('disabled') !== 'disabled') {
            return $('#beforeunload-warning').html();
        }

        return null;
    });

    $('#closing-success .modal-footer > a').click(function () {
        loadExistingGroups();
        initializeNewGroups();
        lightSaveButton();
    });

    $('#closing-success .modal-footer > a + a').click(function () {
        $(window).off('beforeunload');
        top.location =  window.course_groups.launch_presentation_return_url;
    });

    $('button').click(function () {
        var exceptions = window.course_groups.member_exceptions,
            ex = [],
            tpl,
            i;

        $('div.new-group-list > ul > li').each(function(i, e) {
            var group_id = tidyGroupId($('input', e).val());

            if (exceptions.hasOwnProperty(group_id)) {
                ex.push(exceptions[group_id]);
            }
        });

        if (ex.length) {
            tpl = Handlebars.compile($('#closing-modal-exceptions').html());
            $('#closing-success .modal-body div').html(tpl({
                exceptions: ex
            }));
        } else {
            $('#closing-success .modal-body div').html('');
        }

        if (submitGroupChanges()) {
            $('#closing-success').modal();
        }
    });

    var loadCourseRoles = function (account_id) {
        $.ajax({
            type: 'GET',
            dataType: 'json',
            url: 'api/v1/account/' + account_id + '/course_roles',
        }).done(function (data) {
            window.course_groups.roles = data.roles;
            newGroupInput();
            $('div.new-group-list a').click(newGroupInput).show();
        }).fail(function (msg) {
            $('div.new-group-list').html('Error loading course roles: ' + msg);
        }).always(function () {
            $('.loading_roles').hide();  
        });
    };

    var initializeNewGroups = function () {
        window.course_groups.member_exceptions = {};
        $('div.new-group-list ul').html('');

        if (!window.course_groups.roles.length) {
            loadCourseRoles(window.course_groups.canvas_account_id);
        } else {
            newGroupInput();
        }
    };

    var loadExistingGroups = function () {
        // clear table
        $('div.existing-groups table').find('tr:gt(0)').remove();

        $.ajax({
            url: 'api/v1/group/?course_id=' +
                encodeURIComponent(window.course_groups.sis_course_id),
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#existing-group').html()),
                    table = $('div.existing-groups table');

                if (data.hasOwnProperty('groups') && data.groups.length) {
                    $.each(data.groups, function (i) {
                        var j = groupDataFromJSON(data.groups[i]),
                            e = $(tpl(j)),
                            del_link = $('span.group-delete', e),
                            undel_link = $('span.group-undelete', e);

                        table.append(e);

                        $('span.group-delete a', e).click(function (evt) {
                            $(evt.target).closest('tr').addClass('is-deleted');
                            del_link.hide();
                            undel_link.show();
                            lightSaveButton();
                        });

                        $('span.group-undelete a', e).click(function (evt) {
                            $(evt.target).closest('tr').removeClass('is-deleted');
                            del_link.show();
                            undel_link.hide();
                            lightSaveButton();
                        });

                        $(e).hover(function (evt) {
                            if ($(evt.target).closest('tr').hasClass('is-deleted')) {
                                del_link.hide();
                            } else {
                                del_link.show();
                            }
                        }, function (evt) {
                            del_link.hide();
                        });

                        // validate membership
                        $.ajax({
                            type: 'GET',
                            url: 'api/v1/uw/group/' + j.id + '/membership',
                            success: function (data) {
                                var content = validateGroupMembers(
                                        j.group_id, data.invalid,
                                        warnBadExistingGroupMembers),
                                    span;

                                if (content) {
                                    span = $('<span class="group-warning"></span>');
                                    span.popover({
                                        'content': content,
                                        'html': true,
                                        'placement': 'right',
                                        'trigger': 'hover',
                                        'delay': 0
                                    });
                                    $('td:first', e).append(span);
                                }
                            },
                            error: function (xhr, textStatus, errorThrown) {
                                var errstr,
                                    span;

                                try {
                                    errstr = $.parseJSON(xhr.responseText).error;
                                } catch (e) {
                                    errstr = 'Error: ' + xhr.responseText;
                                }

                                span = $('<span class="group-warning"></span>');
                                span.popover({
                                    'content': errstr,
                                    'html': true,
                                    'placement': 'right',
                                    'trigger': 'hover',
                                    'delay': 0
                                });
                                $('td:first', e).append(span);
                            }
                        });
                    });
                    $('div.existing-groups').show();
                } else {
                    $('div.existing-groups').hide();
                }

            },
            error: function (xhr, textStatus, errorThrown) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    // console.log('Group Search Error:' + json.error);
                } catch (e) {
                    // console.log('Unknown error: ' + xhr.responseText);
                }
            }
        });
    };

    // init existing groups
    loadExistingGroups();

    // init new group list
    initializeNewGroups();
});
