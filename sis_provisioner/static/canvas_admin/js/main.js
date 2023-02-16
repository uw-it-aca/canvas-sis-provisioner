/* canvas course admin desktop javascript */

/*jslint browser: true, plusplus: true, regexp: true */
/*global $, jQuery, Handlebars, Highcharts, moment, alert, confirm, startImportMonitoring, stopImportMonitoring, console */

$(document).ready(function () {
    "use strict";
    var hash = window.location.hash;

    if (hash) {
        $('ul.nav a[href="' + hash + '"]').tab('show');
    }

    function openTab() {
        /*jslint validthis: true */
        var scrollmem = $('body').scrollTop();
        window.location.hash = this.hash;
        $('ul.nav a[href="' + this.hash + '"]').tab('show');
        $('html,body').scrollTop(scrollmem);
    }

    $('.nav-tabs a').click(openTab);

    // prep for api post/put
    $.ajaxSetup({
        headers: { "X-CSRFToken": $('input[name="csrfmiddlewaretoken"]').val() }
    });

    // init Highcharts
    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    function format_date(dt) {
        return (dt !== null) ? moment(dt).format("MM/DD/YYYY h:mm a") : '';
    }

    function format_long_date(dt) {
        return (dt !== null) ? moment(dt).format("MMM Do YYYY, h:mm a") : '';
    }

    function format_relative_date(dt) {
        return (dt !== null) ? moment(dt).fromNow() : '';
    }

    function format_hms_date(dt) {
        return moment(dt).format("h:mm:ss a");
    }

    Handlebars.registerHelper("format_relative_date", function(dt) {
        return format_relative_date(dt);
    });

    function initializeSearchForm() {
        var quarters = ['winter', 'spring', 'summer', 'autumn'],
            min_year = 2011,
            max_year = window.canvas_manager.current_term.year + 1,
            years = [];

        for (y = max_year; y >= min_year; y -= 1) {
            years.push(y);
        }

        $('#courseTermYear,#instructorTermYear').each(function () {
            var me = $(this);
            $.each(years, function (i) {
                var selected = (this[i] === window.canvas_manager.current_term.year);
                me.append(new Option(this[i], this[i], selected, selected));
            });
        });

        $('#courseTermQuarter,#instructorTermQuarter').each(function () {
            var me = $(this);
            $.each(quarters, function (i) {
                var selected = (this[i] === window.canvas_manager.current_term.quarter.toLowerCase()),
                    name = this[i].charAt(0).toUpperCase() + this[i].slice(1);
                me.append(new Option(this[i], name, selected, selected));
            });
        });
    }

    function validationButton(group) {
        var button = $('#admin_search_button'),
            commit = function (e) {
                if (e.keyCode === 13) {
                    button.click();
                    e.preventDefault();
                }
            };

        if ($('input.valid-require', group).length === $('input.valid-require.is-valid', group).length) {
            button.removeAttr('disabled');
            $('body').on('keypress', commit);
        } else {
            button.attr('disabled', 'disabled');
            $('body').off('keypress', commit);
        }
    }

    function validationFail(input, event) {
        input.addClass('is-invalid');
        input.removeClass('is-invalid', 500);
        event.preventDefault();
    }

    // set up form validation
    $('input.validate').keydown(function (event) {
        var el = $(this),
            key = event.keyCode,
            v = el.val(),
            l = v.length,
            otherWiseInValid = function (key) {
                return (!(key === 46 || key === 8 || key === 27 ||
                    key === 13 || (key === 65 && event.ctrlKey === true) ||
                    (key >= 35 && key <= 39)));
            };

        if ([9, 27, 13, 16, 17, 18, 91].indexOf(key) >= 0) {
            return;
        }

        el.removeClass('is-valid');
        el.removeClass('is-invalid');
        if (el.hasClass('valid-year')) {
            if (!event.shiftKey && ((key > 47 && key < 58) || (key > 95 && key < 106))) {
                if (l === 3) {
                    el.addClass('is-valid');
                } else if (l > 3) {
                    validationFail(el, event);
                }
            } else if (otherWiseInValid(key)) {
                validationFail(el, event);
            }
        } else if (el.hasClass('valid-alpha')) {
            if (key > 64 && key < 91) {
                el.addClass('is-valid');
            } else if (otherWiseInValid(key)) {
                validationFail(el, event);
            }
        } else if (el.hasClass('valid-alpha-space')) {
            if ((key > 64 && key < 91) || key === 32) {
                el.addClass('is-valid');
            } else if (otherWiseInValid(key)) {
                validationFail(el, event);
            }
        } else if (el.hasClass('valid-num')) {
            if (!event.shiftKey && ((key > 47 && key < 58) || (key > 95 && key < 106))) {
                el.addClass('is-valid');
            } else if (otherWiseInValid(key)) {
                validationFail(el, event);
            }
        } else if (el.hasClass('valid-nonnull')) {
            if (l) {
                el.addClass('is-valid');
            }
        }

        validationButton(el.closest('div.validate-group'));
    });

    // validate on paste too
    $('input.validate').bind('paste', function (ev) {
        var el = $(this);

        setTimeout(function () {
            var v = $(el).val(),
                l = v.length;

            el.removeClass('is-valid');
            el.removeClass('is-invalid');
            if (el.hasClass('valid-year')) {
                if (l === 3) {
                    el.addClass('is-valid');
                } else {
                    validationFail(el, ev);
                }
            } else if (el.hasClass('valid-alpha')) {
                el.addClass('is-valid');
            } else if (el.hasClass('valid-num')) {
                el.addClass('is-valid');
            } else if (el.hasClass('valid-nonnull')) {
                if (l > 0) {
                    el.addClass('is-valid');
                }
            }

            validationButton(el.closest('div.validate-group'));
        }, 100);
    });

    function courseDataFromJSON(course) {
        var is_provisioned = (course.provisioned_date &&
                course.provisioned_date.length && !(course.provisioned_status &&
                course.provisioned_status.length)),
            in_process = false;

        if (course.queue_id && course.queue_id.length) {
            in_process = true;
        }

        if (!$.isArray(course.groups)) {
            course.groups = [];
        }

        return {
            canvas_course_id: course.canvas_course_id,
            course_id: course.course_id,
            primary_id: course.primary_id,
            sws_url: course.sws_url,
            xlist_id: course.xlist_id,
            is_sdb_type: course.is_sdb_type,
            is_provisioned: is_provisioned,
            group_count: course.groups.length,
            group_plural: (course.groups.length > 1) ? 's' : '',
            in_process: in_process,
            provisioned_error: course.provisioned_error,
            provisioned_status: course.provisioned_status,
            added_date: format_long_date(course.added_date),
            added_date_relative: format_relative_date(course.added_date),
            provisioned_date: format_long_date(course.provisioned_date),
            provisioned_date_relative: format_relative_date(course.provisioned_date),
            expiration_date: format_long_date(course.expiration_date),
            expiration_date_relative: format_relative_date(course.expiration_date),
            deleted_date: format_long_date(course.deleted_date),
            deleted_date_relative: format_relative_date(course.deleted_date),
            expiration_exc_granted_date: format_long_date(course.expiration_exc_granted_date),
            expiration_exc_granted_by: course.expiration_exc_granted_by,
            expiration_exc_desc: course.expiration_exc_desc,
            is_expired: course.is_expired
        };
    }

    function doCourseSearch(url, search, container_node) {
        $.ajax({
            url: url,
            dataType: 'json',
            beforeSend: function () {
                container_node.html(Handlebars.compile($('#course-search-wait').html())());
            },
            success: function (data) {
                var tpl = Handlebars.compile($('#course-list-item').html()),
                    context = {
                        header: '',
                        course_count: 0,
                        courses: []
                    };

                if (data.hasOwnProperty('courses')) {
                    context.header = 'Courses' + ((search.term) ? ' matching &quot;' + search.term + '&quot;' : '');
                    if (search.instructor) {
                        context.header += ' for instructor ' + search.instructor;
                    }

                    if (search.queue_id) {
                        context.header += ' matching Import ID ' + search.queue_id;
                    }

                    $.each(data.courses, function () {
                        var course = courseDataFromJSON(this);

                        course.random = Math.floor(Math.random() * 100000000);
                        context.courses.push(course);
                    });
                } else {
                    context.header = 'Course Match';
                    context.courses.push(courseDataFromJSON(data));
                }

                context.course_count = context.courses.length;

                container_node.html(tpl(context));

                $('.xlist-icon, .provisioned-icon, .groups-icon', container_node).popover({ trigger: 'hover' });
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    alert('Course Search Error\n\n' + json.error);
                } catch (e) {
                    console.log('Unknown error: ' + url);
                }
            }
        });
    }

    // submit course search form
    $('#admin_search_button').click(function () {
        var url = '/api/v1/courses?',
            terms = [],
            search_term = '',
            inputs = [{
                id: '#courseCurriculum',
                term: 'curriculum_abbreviation'
            }, {
                id: '#courseNumber',
                term: 'course_number'
            }, {
                id: '#courseSection',
                term: 'section'
            }],
            form = $('div.course-filter ul li.active a'),
            course_id,
            canvas_url,
            instructor_id,
            canvas_id,
            canvas_id_match,
            term_year,
            term_qtr,
            val;

        // collect form values
        if (form.attr('href') === '#search-tab-sisid') {
            course_id = $.trim($('#courseID').val());
            if (course_id !== '') {
                url = '/api/v1/course/' + encodeURIComponent(course_id);
                search_term = 'course ID ' + course_id;
            }
        } else if (form.attr('href') === '#search-tab-canvasurl') {
            canvas_url = $.trim($('#canvasURL').val());
            canvas_id_match = canvas_url.match(/^https:\/\/[\w\W]+\/courses\/(\d+)([\/\?].*)?$/);
            if (canvas_id_match) {
                canvas_id = canvas_id_match[1];
                url = '/api/v1/canvas/course/' + canvas_id;
                search_term = 'Canvas Course ID ' + canvas_id;
            }
        } else if (form.attr('href') === '#search-tab-instructor') {
            instructor_id = $.trim($('#instructorID').val());
            if (instructor_id !== '') {
                terms.push([$('#netregid option:selected').val(), instructor_id].join('='));
                term_year = $('#instructorTermYear option:selected').val();
                term_qtr = $('#instructorTermQuarter option:selected').val();
                terms.push('year=' + encodeURIComponent(term_year));
                terms.push('quarter=' + encodeURIComponent(term_qtr));
                search_term = term_year + '-' + term_qtr;
            }
        } else {
            term_year = $('#courseTermYear option:selected').val();
            term_qtr = $('#courseTermQuarter option:selected').val();
            terms.push('year=' + encodeURIComponent(term_year));
            terms.push('quarter=' + encodeURIComponent(term_qtr));
            search_term = term_year + '-' + term_qtr;

            $.each(inputs, function () {
                var el = form.find(this.id);
                if (el) {
                    val = $.trim($(this.id).val());
                    if (val && val.length) {
                        terms.push([this.term, encodeURIComponent(val)].join('='));
                    }

                    if (search_term.length) {
                        search_term += '-';
                    }
                    search_term += val;
                }
            });
        }

        doCourseSearch(url + terms.join('&'), {
            term: search_term,
            instructor: instructor_id
        }, $('.course-list'));
    });

    $('#import_groups_button').click(function () {
        $.ajax({
            url: '/api/v1/import/',
            contentType: 'application/json',
            type: 'POST',
            processData: false,
            data: JSON.stringify({ "mode": "group" }),
            success: function () {
                alert('Group members being imported');
            },
            error: function (xhr) {
                var json;

                try {
                    json = $.parseJSON(xhr.responseText);
                    alert('Error importing groups:\n    ' + json.error);
                } catch (e) {
                    alert('Error importing groups:\n    ' + xhr.responseText);
                }
            }
        });
    });

    function enrollmentDataFromJSON(enrollment) {
        return {
            reg_id: enrollment.reg_id,
            status: enrollment.status,
            course_id: enrollment.course_id,
            primary_course_id: enrollment.primary_course_id,
            instructor_reg_id: enrollment.instructor_reg_id,
            last_modified: enrollment.last_modified ? $.datepicker.formatDate('MM d, yy', enrollment.date_modified) : null
        };
    }

    function doEnrollmentSearch(url, search, container_node) {
        $.ajax({
            url: url,
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#enrollment-list-item').html()),
                    context = {
                        header: '',
                        enrollment_count: 0,
                        enrollments: []
                    };

                if (data.hasOwnProperty('enrollments')) {
                    context.header = 'Enrollments' + ((search.term) ? ' matching &quot;' + search.term + '&quot;' : '');
                    if (search.instructor) {
                        context.header += ' for instructor ' + search.instructor;
                    }

                    if (search.queue_id) {
                        context.header += ' matching Import ID ' + search.queue_id;
                    }

                    $.each(data.enrollments, function () {
                        var enrollment = enrollmentDataFromJSON(this);

                        enrollment.random = Math.floor(Math.random() * 100000000);
                        context.enrollments.push(enrollment);
                    });
                } else {
                    context.header = 'Enrollment Match';
                    context.enrollments.push(enrollmentDataFromJSON(data));
                }

                context.enrollment_count = context.enrollments.length;

                container_node.html(tpl(context));

                $('.xlist-icon, .provisioned-icon, .groups-icon', container_node).popover({ trigger: 'hover' });
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    alert('Course Search Error\n\n' + json.error);
                } catch (e) {
                    console.log('Unknown error: ' + url);
                }
            }
        });
    }

    function renderUserInfo(data) {
        var tpl = Handlebars.compile($('#user-info').html());

        if (data.added_date) {
            data.added_date = format_long_date(data.added_date) +
                ' (' + format_relative_date(data.added_date) + ')';
        } else {
            data.added_date = false;
        }

        if (data.provisioned_date) {
            data.provisioned_date = format_long_date(data.provisioned_date) +
                ' (' + format_relative_date(data.provisioned_date) + ')';
        } else {
            data.provisioned_date = false;
        }
        $('div#user_search_result div').removeClass('waiting').html(tpl(data));
    }

    // user search
    $('#user_search_id').change(function (e) {
        var o_user_id = $('#userID'),
            which;

        if (!o_user_id.val().length) {
            which = $(e.target).val();
            o_user_id.attr('placeholder', (which === 'gmail_id') ?
                'user@gmail.com' : (which === 'reg_id') ?
                '9136CCB8F66711D5BE060004AC494FFE' : 'javerage');
        }
    });

    $('#user_search_button').click(function () {
        var url = '/api/v1/users',
            result_div = $('div#user_search_result div'),
            user_id = $('#userID').val(),
            which = $('#user_search_id').val();

        if (user_id.length) {
            $('div#user_search_result').show();
        } else {
            $('div#user_search_result').hide();
            return;
        }

        result_div.addClass('waiting');
        result_div.html('&nbsp;');

        if (which === 'gmail_id') {
            url += '?gmail_id=';
        } else if (which === 'net_id') {
            url += '?net_id=';
        } else if (which === 'reg_id') {
            url += '?reg_id=';
        } else {
            return;
        }

        $.ajax({
            url: url + user_id,
            dataType: 'json',
            success: function (data) {
                var privileged_actions = $('#user-privileged-actions');

                renderUserInfo(data);

                if (privileged_actions.length) {
                    var tpl = Handlebars.compile(privileged_actions.html());
                    $(".privileged-actions", result_div).html(tpl(data));
                }

                $('#user_add_button').click(function () {
                    var adding = '',
                        json = {};

                    switch ($('#user_search_id :selected').val()) {
                    case 'gmail_id':
                        json.gmail_id = data.gmail_id;
                        adding = 'Gmail user ' + data.gmail_id;
                        break;
                    case 'net_id':
                        json.net_id = data.net_id;
                        adding = 'UW NetId ' + data.net_id;
                        break;
                    case 'reg_id':
                        json.reg_id = data.reg_id;
                        adding = 'UW RegId ' + data.reg_id;
                        break;
                    default:
                        console.log('unknown user type');
                        break;
                    }

                    result_div.html('Adding ' + adding + ' ...');

                    $.ajax({
                        url: '/api/v1/users/',
                        contentType: 'application/json',
                        type: 'POST',
                        processData: false,
                        data: JSON.stringify(json),
                        success: function () {
                            result_div.html(adding + ' has been provisioned to UW Canvas.');
                        },
                        error: function (xhr) {
                            var response_json;

                            try {
                                response_json = $.parseJSON(xhr.responseText);
                                result_div.html(response_json.error);
                            } catch (e) {
                                result_div.html('ERROR: ' + xhr.responseText);
                            }
                        }
                    });
                });
            },
            error: function (xhr) {
                var json;

                result_div.removeClass('waiting');
                try {
                    json = $.parseJSON(xhr.responseText);
                    result_div.html('Search failed: ' + json.error);
                } catch (e) {
                    result_div.html('Search failed: ' + xhr.responseText);
                }
            }
        });

    });

    // import status list
    function loadImportStatus() {
        $.ajax({
            url: '/api/v1/imports',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#import-list-item').html()),
                    context = {
                        import_count: (data.hasOwnProperty('imports')) ? data.imports.length : 0,
                        imports: []
                    };

                if (context.import_count > 0) {
                    $.each(data.imports, function (i) {
                        var imp = this,
                            exception_failure = (imp.post_status < 0),
                            csv_failure = (imp.csv_errors && imp.csv_errors.length),
                            post_failure = (imp.post_status !== null &&
                                            imp.post_status !== 200 &&
                                            imp.canvas_errors &&
                                            imp.canvas_errors.length),
                            canvas_state = imp.canvas_state || '',
                            canvas_failed = (canvas_state.match(/^failed/) !== null),
                            output = [],
                            raw_output = '',
                            json;

                        if (csv_failure) {
                            output.push({
                                type: 'Message',
                                message: imp.csv_errors
                            });
                        } else if (post_failure) {
                            output.push({
                                type: 'Message',
                                message: imp.canvas_errors
                            });
                        } else {
                            try {
                                if (imp.canvas_warnings) {
                                    json = $.parseJSON(imp.canvas_warnings);
                                    raw_output += JSON.stringify(
                                        {'processing_warnings': json}, null, '    ');
                                    $.each(json, function (i) {
                                        output.push({
                                            type: this[0],
                                            message: this[1]
                                        });
                                    });
                                }

                                if (imp.canvas_errors) {
                                    json = $.parseJSON(imp.canvas_errors);
                                    raw_output += JSON.stringify(
                                        {'processing_errors': json}, null, '    ');
                                    $.each(json, function (i) {
                                        output.push({
                                            type: this[0],
                                            message: this[1]
                                        });
                                    });
                                }
                            } catch (err) {
                                output.push({
                                    type: 'Message',
                                    message: imp.canvas_errors || imp.canvas_warnings
                                });
                            }
                        }

                        context.imports.push({
                            'type': imp.type,
                            'type_name': imp.type_name,
                            'queue_id': imp.queue_id,
                            'added_date': moment(imp.added_date).format("MMM Do, h:mm a"),
                            'added_date_relative': moment(imp.added_date).fromNow(),
                            'priority': imp.priority,
                            'high_priority': (imp.priority === 'high'),
                            'immediate_priority': (imp.priority === 'immediate'),
                            'exception_failure': exception_failure,
                            'csv_failed': csv_failure,
                            'post_failed': post_failure,
                            'import_failed': (post_failure || canvas_failed || csv_failure),
                            'canvas_finished': (canvas_state.match(/^(imported|failed)/) !== null),
                            'timeout_exceeded': moment().diff(moment(imp.added_date), 'hours'),
                            'with_messages': (canvas_state.match(/^(imported|failed)_with_messages/) !== null),
                            'is_pending': (imp.csv_path !== null &&
                                           imp.post_status === null &&
                                           !(csv_failure || post_failure)),
                            'post_status': imp.post_status,
                            'canvas_state': canvas_state,
                            'in_progress': (imp.canvas_progress && imp.canvas_progress !== 100),
                            'canvas_progress': imp.canvas_progress,
                            'has_canvas_output': (output.length > 0 || raw_output),
                            'canvas_output': output,
                            'raw_canvas_output': raw_output
                        });
                    });

                    $('#import-count').show();
                    $('#import-count').html(context.import_count);
                } else {
                    $('#import-count').hide();
                }

                $('.import-list').parent().removeClass('waiting');
                $('.import-list').html(tpl(context));

                // attach progress updating
                $('.progress-bar').each(function () {
                    var bar = $(this),
                        date = new Date(),
                        bar_id = 'bar_' + date.getTime(),
                        import_id = bar.attr('data-import-id'),
                        timer_id;

                    bar.attr('data-bar-id', bar_id);

                    timer_id = setInterval(function () {
                        if ($('[data-bar-id="' + bar_id + '"][data-import-id="' + import_id + '"]').length) {
                            $.ajax({
                                url: '/api/v1/import/' + import_id,
                                contentType: 'application/json',
                                type: 'GET',
                                success: function (data) {
                                    bar.css('width', data.canvas_progress + '%')
                                        .attr('aria-valuenow', data.canvas_progress);
                                    bar.find('span').text(data.canvas_progress);
                                    if (data.canvas_progress >= 100) {
                                        clearInterval(timer_id);
                                    }
                                },
                                error: function () {
                                    clearInterval(timer_id);
                                }
                            });
                        } else {
                            clearInterval(timer_id);
                        }
                    }, 1000);
                });

                $('p.import-update > span:first').html(format_hms_date());
                $('p.import-update > span + a + span').html(window.canvas_manager.import_update_frequency);
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('import service error:' + json.error);
                } catch (e) {
                    console.log('Unknown event service error');
                }
            }
        });
    }

    function loadProvisionedErrors() {
        $.ajax({
            url: '/api/v1/courses?provisioned_error=true',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#provision-error-list-item').html()),
                    context = {
                        errors: []
                    };

                if (data.hasOwnProperty('courses')) {
                    $.each(data.courses, function (i) {
                        var course = data.courses[i];

                        // Display courses with provisioned_status, but not
                        // withdrawn sections
                        if (course.provisioned_status !== null &&
                                course.provisioned_status.match(/No section found./) === null) {
                            context.errors.push({
                                type: 'Course',
                                course_id: course.course_id,
                                priority: course.priority,
                                provisioned_status: course.provisioned_status
                            });
                        }
                    });

                    $('#course-error-count').show();
                    $('#course-error-count').html(context.errors.length);
                    $('p.error-update span').html(format_hms_date());
                } else {
                    $('#course-error-count').hide();
                }

                $('ul.provision-error-list').parent().removeClass('waiting');
                $('ul.provision-error-list').html(tpl(context));
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('import service error:' + json.error);
                } catch (e) {
                    console.log('Unknown event service error');
                }
            }
        });
    }

    function initializeImportEvents() {
        Handlebars.registerPartial('raw-output-link', $('#raw-output-link-partial').html());

        $('.import-status').on('click', 'a.examine-import', function (e) {
            var $a = $(e.target),
                $li = $a.closest('li'),
                queue_id = $li.attr('id').match(/canvas_import_(\d+)/)[1];

            // search by type
            switch ($a.attr('data-type').toLowerCase()) {
            case 'course':
                doCourseSearch('/api/v1/courses?queue_id=' +
                    queue_id, { queue_id: queue_id },
                    $('.status-result-list'));
                break;
            case 'enrollment':
                doEnrollmentSearch('/api/v1/enrollments?queue_id=' +
                    queue_id, { queue_id: queue_id },
                    $('.status-result-list'));
                break;
            default:
                break;
            }
        }).on('click', 'a.action', function (e) {
            var $li = $(e.target).closest('li'),
                queue_id = $li.attr('id').match(/canvas_import_(\d+)/)[1],
                msg;

            msg = 'Remove status message and ';
            if ($li.find('.import-fail').length) {
                msg += 're-queued items for import?';
            } else {
                msg += 'assign provision dates?';
            }

            msg += '\n\nOnly click OK if you KNOW WHAT YOU ARE DOING.';

            if (confirm(msg)) {
                $.ajax({
                    url: '/api/v1/import/' + queue_id,
                    contentType: 'application/json',
                    type: 'DELETE',
                    beforeSend: stopImportMonitoring
                }).always(startImportMonitoring)
                    .fail(function (xhr) {
                        try {
                            alert($.parseJSON(xhr.responseText).error);
                        } catch (e) {
                            alert('ERROR: ' + xhr.responseText);
                        }
                    });
            }
        }).on('click', '.has-response', function (e) {
            var $raw = $(e.target).closest('li').find('.raw-output');

            e.preventDefault();
            if ($raw.length) {
                if ($raw.hasClass('hidden')) {
                    $raw.removeClass('hidden');
                    $raw.next().addClass('hidden');
                } else {
                    $raw.addClass('hidden');
                    $raw.next().removeClass('hidden');
                }
            }
        });
    }

    function importMonitor() {
        var state = window.canvas_manager;

        loadImportStatus();
        loadProvisionedErrors();
        if (state.hasOwnProperty('importCountdownId') && state.importCountdownId) {
            clearInterval(state.importCountdownId);
        }

        state.importCountdown = window.canvas_manager.import_update_frequency;
        state.importCountdownId = setInterval(function () {
            state.importCountdown -= 1;
            if (state.importCountdown >= 0) {
                $('p.import-update > span + a + span').html(state.importCountdown);
            }
        }, 1000);
    }

    function startImportMonitoring() {
        var state = window.canvas_manager;

        importMonitor();
        state.importTimerId = setInterval(importMonitor,
                                          state.import_update_frequency * 1000);
    }

    function stopImportMonitoring() {
        var state = window.canvas_manager;

        if (state.hasOwnProperty('importTimerId') && state.importTimerId) {
            clearInterval(state.importTimerId);
        }
    }

    function toggleJob() {
        /*jslint validthis: true */
        var input = $(this);

        if (input.attr('data-display-only')) {
            return;
        }

        $.ajax({
            url: '/api/v1/job/' + encodeURIComponent(input.attr('data-job-id')),
            contentType: 'application/json',
            type: 'PUT',
            processData: false,
            data: '{"job": {"is_active": ' + $(this).is(':checked') + '}}',
            success: function (data) {
                if (data.hasOwnProperty('job')) {
                    input.closest('td').prev()
                         .html(format_date(data.job.changed_date) +
                               ' (' + data.job.changed_by + ')');
                }
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('Event service error:' + json.error);
                } catch (e) {
                    console.log('Unknown job service error');
                }
            }
        });
    }

    function deleteJob() {
        /*jslint validthis: true */
        var btn = $(this),
            msg = 'Permanently delete this job?';
        if (confirm(msg)) {
            $.ajax({
                url: '/api/v1/job/' + encodeURIComponent(btn.attr('data-job-id')),
                contentType: 'application/json',
                type: 'DELETE',
                success: function () {
                    btn.closest('tr').remove();
                },
                error: function (xhr) {
                    var json;
                    try {
                        json = $.parseJSON(xhr.responseText);
                        console.log('Event service error:' + json.error);
                    } catch (e) {
                        console.log('Unknown job service error');
                    }
                }
            });
        }
    }

    function loadJobs() {
        $.ajax({
            url: '/api/v1/jobs',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#job-table-row').html()),
                    context = {jobs: []};
                if (data.hasOwnProperty('jobs')) {
                    $.each(data.jobs, function (i) {
                        var job = data.jobs[i];
                        context.jobs.push({
                            job_id: job.job_id,
                            name: job.name,
                            title: job.title,
                            is_active: job.is_active ? true : false,
                            changed_by: job.changed_by,
                            changed_date: job.changed_date ? format_date(job.changed_date) : null,
                            last_run_date: job.last_run_date ? format_date(job.last_run_date) : null,
                            read_only: job.read_only
                        });
                    });
                    $('#jobs-table tbody').html(tpl(context));
                    $('#jobs-table tbody input.toggle-job').each(function () {
                        $(this).bootstrapToggle().change(toggleJob);
                    });
                    $('#jobs-table tbody button.delete-job').click(deleteJob);
                    $('#jobs-table').dataTable({
                        'aaSorting': [[ 0, 'asc' ]],
                        'bPaginate': false,
                        'searching': false,
                        'bScrollCollapse': true
                    });
                }
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('admin service error:' + json.error);
                } catch (e) {
                    console.log('Unknown admin service error');
                }
            }
        });
    }

    function reLoadJobs() {
        $.ajax({
            url: '/api/v1/jobs',
            contentType: 'application/json',
            type: 'GET',
            success: function (data) {
                if (data.hasOwnProperty('jobs')) {
                    $.each(data.jobs, function () {
                        var job = this;

                        $('#jobs-table tr > td').filter(function() {
                            var $title = $(this),
                                $row = $title.parent(),
                                $toggle;

                            if ($title.text() === job.title) {
                                $row.find('.last-run-date').text(format_date(job.last_run_date));
                                $row.find('.last-change-date').text(format_date(job.changed_date));
                                $row.find('.last-change-by').text(job.changed_by);
                                $toggle = $row.find('input.toggle-job');
                                if (job.is_active) {
                                    if (!$toggle.prop('checked')) {
                                        $toggle.
                                            attr('data-display-only', '1').
                                            bootstrapToggle('on').
                                            removeAttr('data-display-only');
                                    }
                                } else if ($toggle.prop('checked')) {
                                    $toggle.
                                        attr('data-display-only', '1').
                                        bootstrapToggle('off').
                                        removeAttr('data-display-only');
                                }

                                return false;
                            }
                        });
                    });
                }
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('admin service error:' + json.error);
                } catch (e) {
                    console.log('Unknown admin service error');
                }
            }
        });
    }

    function loadAdmins() {
        $.ajax({
            url: '/api/v1/admins',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#admin-table-row').html()),
                    context = {
                        admins: []
                    },
                    n;

                if (data.hasOwnProperty('admins')) {
                    n = 0;
                    $.each(data.admins, function (i) {
                        var admin = data.admins[i];

                        if (!admin.is_deleted) {
                            n++;
                        }

                        context.admins.push({
                            net_id: admin.net_id,
                            role: admin.role,
                            account_id: admin.account.sis_id || admin.account.canvas_id,
                            account_link: admin.account.canvas_url,
                            added_date: admin.added_date,
                            is_deleted: admin.is_deleted
                        });
                    });

                    $('#admin-count').show();
                    $('#admin-count').html(n);
                } else {
                    $('#admin-count').hide();
                }

                $('.admin-table').parent().removeClass('waiting');
                $('.admin-table tbody').html(tpl(context));
                $('.admin-table').dataTable({
                    "aaSorting": [[ 0, "asc" ]],
                    //"sScrollY": "180px",
                    "bPaginate": false,
                    "bScrollCollapse": true,
                    "initComplete": function () {
                        var api = this.api();

                        api.column(4).search('^$', true).draw();

                        $('#show-deleted')
                            .prependTo('#admin-table_filter')
                            .show()
                            .find('input')
                            .change(function () {
                                api.column(4).search(this.checked ? '^$' : '',
                                                     true).draw();
                            });
                    }
                });
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('admin service error:' + json.error);
                } catch (e) {
                    console.log('Unknown admin service error');
                }
            }
        });
    }

    function loadGroups() {
        $.ajax({
            url: '/api/v1/groups',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#group-table-row').html()),
                    context = {
                        groups: []
                    },
                    n;

                if (data.hasOwnProperty('groups')) {
                    n = 0;
                    $.each(data.groups, function (i) {
                        var group = data.groups[i];

                        if (!group.is_deleted) {
                            n++;
                        }

                        context.groups.push({
                            group_id: group.group_id,
                            role: group.role,
                            course_id: group.course_id,
                            added_by: group.added_by,
                            added_date: format_date(group.added_date),
                            is_deleted: group.is_deleted,
                            deleted_by: group.deleted_by,
                            deleted_date: format_date(group.deleted_date),
                            updated_date: format_date(group.provisioned_date)
                        });
                    });

                    $('#group-count').show();
                    $('#group-count').html(n);
                } else {
                    $('#group-count').hide();
                }

                $('.group-table').parent().removeClass('waiting');
                $('.group-table tbody').html(tpl(context));
                $('.group-table').dataTable({
                    "aaSorting": [[ 0, "asc" ]],
                    //"sScrollY": "180px",
                    "bPaginate": false,
                    "bScrollCollapse": true,
                    "initComplete": function () {
                        var api = this.api();

                        api.column(6).search('^$', true).draw();

                        $('#show-deleted')
                            .prependTo('#group-table_filter')
                            .show()
                            .find('input')
                            .change(function () {
                                api.column(6).search(this.checked ? '^$' : '',
                                                     true).draw();
                            });
                    }
                });

                $('.group-table tbody .canvas-course-link').on('click', function (e) {
                    var target_node = $(e.target),
                        course_id = target_node.attr('data-course-id'),
                        canvas_id_match = course_id.match(/^course_(\d+)$/);

                    e.preventDefault();

                    if (canvas_id_match) {
                        course_id = canvas_id_match[1];
                    }

                    $.ajax({
                        url: '/api/v1/canvas/course/' + course_id,
                        dataType: 'json',
                        success: function (data) {
                            window.open(data.course_url);
                        },
                        error: function (xhr) {
                            try {
                                var json = $.parseJSON(xhr.responseText);
                                alert('Unable to load Canvas course data: ' + json.error);
                            } catch (e) {
                                alert('Unable to load Canvas course data');
                            }
                        }
                    });

                    return false;
                });
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('group service error:' + json.error);
                } catch (e) {
                    console.log('Unknown group service error');
                }
            }
        });
    }

    function updateCourseListCanvasLinks(course_body) {
        var link = $('a.canvas-course-link', course_body);

        if (link.length && link.attr('data-course-id')) {
            $.ajax({
                url: '/api/v1/canvas/course/' + link.attr('data-course-id'),
                dataType: 'json',
                success: function (data) {
                    var state_node = $('.workflow_state', course_body),
                        icon_node = state_node.prev('i');

                    link.attr('href', data.course_url);

                    if (icon_node.hasClass('fa-spinner')) {
                        icon_node.removeClass('fa-spinner fa-spin').addClass('fa-newspaper-o');
                    }

                    switch (data.workflow_state) {
                    case 'available':
                        state_node.html('is published');
                        icon_node.addClass('course-available');
                        break;
                    case 'completed':
                        state_node.html('is completed');
                        icon_node.addClass('course-emphasis');
                        break;
                    default:
                        state_node.html('is NOT yet published');
                        icon_node.addClass('course-pending');
                        break;
                    }

                    updateCourseListSubAccount(data.account_id, course_body);
                },
                error: function (xhr) {
                    var state_node = $('.workflow_state', course_body),
                        icon_node = state_node.prev('i'),
                        json;

                    if (icon_node.hasClass('fa-spinner')) {
                        icon_node.removeClass('fa-spinner fa-spin').addClass('fa-question');
                    }

                    try {
                        json = $.parseJSON(xhr.responseText);
                        alert('Unable to load Canvas course data: ' + json.error);
                    } catch (e) {
                        alert('Unable to load Canvas course data');
                    }
                }
            });
        }
    }

    function updateCourseListURL(a, course_sis_id) {
        $.ajax({
            url: '/api/v1/canvas/course/' + course_sis_id,
            dataType: 'json',
            success: function (data) {
                a.attr('href', data.course_url);
            },
            error: function (xhr) {
                try {
                    var json = $.parseJSON(xhr.responseText);
                    alert('Unable to view Canvas course: ' + json.error);
                } catch (e) {
                    alert('Unable to view Canvas course');
                }
            }
        });
    }

    function updateCourseListSubAccount(account_id, course_body) {
        $.ajax({
            url: '/api/v1/canvas/account/' + account_id,
            dataType: 'json',
            success: function (data) {
                $('li.canvas-subaccount', course_body).show();
                $('li.canvas-subaccount span', course_body).html(data.name);
                $('li.canvas-subaccount a', course_body).attr('href', data.account_url);
            },
            error: function (xhr) {
                try {
                    var json = $.parseJSON(xhr.responseText);
                    alert('Unable to view Canvas course: ' + json.error);
                } catch (e) {
                    alert('Unable to view Canvas course');
                }
            }
        });
    }

    function initializeUserSearchEvents() {
        var container = $('#user-search');

        container.on('click', 'button.terminate-sessions', function (e) {
            var $button = $(this),
                netid = $button.attr('data-net-id'),
                canvas_user_id = $button.attr('data-user-id');

            if (window.confirm("Really terminate " + netid + " Canvas' sessions?")) {
                $.ajax({
                    url: '/api/v1/users/' + canvas_user_id + '/sessions',
                    contentType: 'application/json',
                    type: 'DELETE',
                    processData: false,
                    success: function () {
                        alert("User " + netid + " sessions have been terminated.");
                    },
                    error: function (xhr) {
                        alert('Cannot terminate sessions: ' + xhr.responseText);
                    }
                });
            }
        });

        container.on('click', 'button.merge-users', function (e) {
            var $button = $(this),
                regid = $button.attr('data-reg-id'),
                is_sis_update = $button.attr('data-sis-update'),
                confirmation = (is_sis_update) ?
                    'The SIS ID for this user will be updated to the current UWRegID.' :
                    'These Canvas users will be merged. Proceed?';

            if (window.confirm(confirmation)) {
                $.ajax({
                    url: '/api/v1/users/' + regid + '/merge',
                    type: 'PUT',
                    processData: false,
                    success: function (data) {
                        renderUserInfo(data);
                    },
                    error: function (xhr) {
                        if (is_sis_update) {
                            alert('Update failed: ' + xhr.responseText);
                        } else {
                            alert('Merge failed: ' + xhr.responseText);
                        }
                    }
                });
            }
        });
    }

    function initializeCourseListEvents() {
        var container = $('.course-list, .status-result-list');

        container.on('show.bs.collapse', '#course-accordion, #enrollment-accordion', function (e) {
            var course_body = $(e.target),
                course_header = course_body.prev();

            updateCourseListCanvasLinks(course_body);

            course_header.find('.accordion-toggle i').toggleClass('fa-chevron-right fa-chevron-down');
        }).on('hide.bs.collapse', '#course-accordion', function (e) {
            $(e.target).prev().find('.accordion-toggle i').toggleClass('fa-chevron-down fa-chevron-right');
        }).on('click', '.accordion-toggle', function (event) {
            event.preventDefault();
        }).on('click', 'a.sis-course-link', function (e) {
            var a = $(e.target).closest('a');

            updateCourseListURL(a, a.attr('data-course-id'));
        }).on('click', 'button.provision-course', function (e) {
            var button = $(e.target).closest('button'),
                button_updating = function (b) {
                    b.removeClass('btn-default');
                    b.removeClass('btn-success');
                    b.addClass('btn-warning');
                    b.html('<i class="icon-time icon-white"></i> Updating');
                };

            button.attr('disabled', 'disabled');

            $.ajax({
                url: '/api/v1/course/' + encodeURIComponent(button.attr('data-course-id')),
                contentType: 'application/json',
                type: 'PUT',
                processData: false,
                data: '{ "priority": "immediate" }',
                success: function () {
                    button_updating(button);
                },
                error: function (xhr) {
                    var json;

                    try {
                        json = $.parseJSON(xhr.responseText);
                        if (json.error.match(/ being provisioned$/)) {
                            button_updating(button);
                        } else {
                            button.removeAttr('disabled');
                        }
                        console.log('Event service error:' + json.error);
                    } catch (e) {
                        console.log('Unknown course service error');
                    }
                }
            });
        });
    }

    function canvasStatusMonitor() {
        $.ajax({
            url: '/api/v1/canvas',
            dataType: 'json',
            success: function (data) {
                var tpl = Handlebars.compile($('#canvas-system-status').html());

                $('.canvas-status').html(tpl({
                    url: data[0].url,
                    overall_state: data[0].state,
                    overall_status: data[0].status,
                    components: data.slice(1)
                }));
            }
        });
    }

    function startCanvasStatusMonitor() {
        canvasStatusMonitor();
        setInterval(canvasStatusMonitor, 5 * 60 * 1000);
    }

    function termDatesMonitor() {
        $.ajax({
            url: '/api/v1/terms',
            dataType: 'json',
            success: function (data) {
                var now = moment(),
                    current = data.terms.current,
                    next = data.terms.next,
                    first_day = moment(current.first_day_quarter),
                    last_day = moment(current.grade_submission_deadline),
                    current_registrations = current.registration_periods,
                    next_registrations = next.registration_periods,
                    context = current.label,
                    enrollments,
                    when = 'next';

                if (now.diff(first_day) > 0) {
                    context += ' ends ' + last_day.fromNow();
                } else {
                    context += ' starts ' + first_day.fromNow();
                }

                enrollments = moment(current_registrations[0].start);
                if (now.diff(enrollments) > 0) {
                    enrollments = moment(current_registrations[1].start);
                    if (now.diff(enrollments) > 0) {
                        enrollments = moment(current_registrations[2].start);
                        if (current.label != next.label && now.diff(enrollments) > 0) {
                            when = next.label;
                            enrollments = moment(next_registrations[0].start);
                            if (now.diff(enrollments) > 0) {
                                enrollments = moment(next_registrations[1].start);
                                if (now.diff(enrollments) > 0) {
                                    enrollments = moment(next_registrations[2].start);
                                }
                            }
                        }
                    }
                }

                context += ', ' + when + ' registration period starts ' + enrollments.fromNow();
                $('#term-info').html(context);
            }
        });
    }

    function startTermDatesMonitor() {
        termDatesMonitor();
        setInterval(termDatesMonitor, 8 * 60 * 60 * 1000);
    }

    // event frequency chart
    function initializeStripAndGauge(event_types) {
        var url_base = '/api/v1/events?type=' + event_types.join(',') + '&',
            gauge = new Highcharts.Chart({
                chart: {
                    renderTo: 'event-gauge',
                    type: 'gauge',
                    plotBorderWidth: 1,
                    plotBackgroundColor: {
                        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                        stops: [
                            [0, '#FFF4C6'],
                            [0.3, '#FFFFFF'],
                            [1, '#FFF4C6']
                        ]
                    },
                    plotBackgroundImage: null,
                    height: 200,
                    width: 420
                },
                title: {
                    text: null
                },
                tooltip: {
                    shared: true
                },
                credits: {
                    enabled: false
                },
                pane: [{
                    startAngle: -45,
                    endAngle: 45,
                    background: null,
                    center: ['50%', '150%'],
                    size: 400
                }],

                yAxis: [{
                    type: 'logarithmic',
                    min: 1,
                    max: 10000,
                    minorTickPosition: 'outside',
                    tickPosition: 'outside',
                    minorTickInterval: 0.1,
                    labels: {
                        rotation: 'auto',
                        distance: 20
                    },
                    plotBands: [{
                        from: 4000,
                        to: 7000,
                        color: '#FFFF00',
                        innerRadius: '100%',
                        outerRadius: '105%'
                    }, {
                        from: 7000,
                        to: 10000,
                        color: '#C02316',
                        innerRadius: '100%',
                        outerRadius: '105%'
                    }],
                    pane: 0,
                    title: {
                        text: 'events / hour',
                        y: -40
                    }
                }, {
                    type: 'logarithmic',
                    pane: 0
                }],

                plotOptions: {
                    gauge: {
                        dataLabels: {
                            enabled: false
                        },
                        dial: {
                            radius: '100%'
                        },
                        tooltip: {
                            followPointer: true
                        }
                    }
                },
                series: [{
                    name: 'per hour',
                    data: [0],
                    yAxis: 0,
                    dial: {
                        backgroundColor: '#000000'
                    }
                }, {
                    name: 'per hour (over 6 hours)',
                    data: [0],
                    yAxis: 0,
                    dial: {
                        backgroundColor: '#00CC00'
                    }
                }]
            }),
            updateGauge = function (data) {
                var last_hour = 0,
                    avg_hours = 0,
                    hours_to_avg = 6,
                    n,
                    i;

                n = data.length - 60;

                if (n > 0) {
                    for (i = n; i < data.length; i += 1) {
                        last_hour += data[i].y;
                    }

                    i = (n - (60 * (hours_to_avg - 1)));
                    if (i >= 0) {
                        avg_hours = last_hour;
                        while (i < n) {
                            avg_hours += data[i].y;
                            i += 1;
                        }
                    }
                }

                gauge.series[0].setData([last_hour], true);
                gauge.series[1].setData([Math.ceil(avg_hours / hours_to_avg)], true);
                gauge.redraw();
            },
            chart,
            chart_config = {
                chart: {
                    renderTo: 'event-graph',
                    zoomType: 'x',
                    spacingRight: 8,
                    events: {
                        load: function () {
                            var chart = this;

                            setInterval(function () {
                                var now = new Date();

                                now.setSeconds(0); // normalize for resolution
                                now.setMilliseconds(0);

                                $.ajax({
                                    url: url_base + 'on=' + moment.utc(now).toISOString(),
                                    dataType: 'json',
                                    success: function (data) {
                                        var types = event_types.length,
                                            rate = new Array(chart.series[0].data.length),
                                            last,
                                            point,
                                            total = 0,
                                            max = 0,
                                            sum = 0,
                                            i, j;

                                        if (chart.series[0].data.length) {
                                            for (i = 0; i < types; i += 1) {
                                                last = chart.series[i].data[chart.series[i].data.length - 1];
                                                point = data[event_types[i]].points[0];
                                                total += point;
                                                if (last.x === now.getTime()) {
                                                    last.y = point;
                                                } else {
                                                    chart.series[i].addPoint([now.getTime(), point], true, true);
                                                }

                                                for (j = 0; j < chart.series[i].data.length; j += 1) {
                                                    sum += chart.series[i].data[j].y;

                                                    if (rate[j]) {
                                                        rate[j].y += chart.series[i].data[j].y;
                                                    } else {
                                                        rate[j] = {x: chart.series[i].data[j].x,
                                                                   y: chart.series[i].data[j].y};
                                                    }

                                                    if (max < rate[j].y) {
                                                        max = rate[j].y;
                                                    }
                                                }
                                            }

                                            last = chart.series[types].data[chart.series[types].data.length - 1];
                                            if (last.x === now.getTime()) {
                                                last.y += total;
                                            } else {
                                                chart.series[types].addPoint([now.getTime(), last.y + total], true, true);
                                            }

                                            if (total > max) {  // rescale
                                                chart.yAxis[0].setExtremes(0, total);
                                                chart.yAxis[1].setExtremes(0, sum);
                                            }

                                            $('#event-count').html(sum);
                                            updateGauge(rate);
                                        }
                                    },
                                    error: function (xhr) {
                                        var json;

                                        try {
                                            json = $.parseJSON(xhr.responseText);
                                            console.log('Event service error:' + json.error);
                                        } catch (e) {
                                            console.log('Unknown event service error');
                                        }
                                    }
                                });
                            }, window.canvas_manager.event_update_frequency * 1000);
                        }
                    },
                    resetZoomButton: {
                        position: {
                            align: 'left',
                            // verticalAlign: 'top', // by default
                            x: 0,
                            y: -6
                        }
                    }
                },
                title: {
                    text: null
                },
                xAxis: [{
                    type: 'datetime',
                    maxZoom: 5 * 60 * 1000, // five minutes
                    title: {
                        text: null
                    },
                    events: {
                        setExtremes: function (event) {
                            var types = event_types.length,
                                data = chart.series[0].data,
                                min = event.min ? Math.floor(event.min) : this.dataMin,
                                max = event.max ? Math.ceil(event.max) : this.dataMax,
                                sum = 0,
                                i, ii;

                            for (i = 0; i < data.length && data[i].x <= max; i += 1) {
                                if (data[i].x >= min) {
                                    for (ii = 0; ii < types; ii += 1) {
                                        sum += chart.series[ii].data[i].y;
                                    }
                                }

                                chart.series[types].data[i].y = sum;
                            }

                            chart.yAxis[1].setExtremes(0, sum);
                            $('#event-count').html(sum);
                        }
                    }
                }],
                yAxis: [{
                    title: {
                        text: 'per minute'
                    },
                    min: 0,
                    minRange: 1,
                    allowDecimals: false,
                    startOnTick: false,
                    showFirstLabel: false,
                    minPadding: 0.2
                }, {
                    title: {
                        text: 'cumulative'
                    },
                    min: 0,
                    minRange: 100,
                    allowDecimals: false,
                    startOnTick: false,
                    showFirstLabel: false,
                    minPadding: 0.2,
                    opposite: true
                }],
                tooltip: {
                    shared: true
                },
                legend: {
                    enabled: false
                },
                credits: {
                    enabled: false
                },
                plotOptions: {
                    column: {
                        stacking: 'normal'
                    },
                    area: {
                        fillColor: {
                            linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1},
                            stops: [
                                [0, Highcharts.getOptions().colors[0]],
                                [1, 'rgba(2,0,0,0)']
                            ]
                        },
                        lineWidth: 1,
                        marker: {
                            enabled: false,
                            states: {
                                hover: {
                                    enabled: true,
                                    radius: 5
                                }
                            }
                        },
                        shadow: false,
                        states: {
                            hover: {
                                lineWidth: 1
                            }
                        }
                    }
                }
            },
            pointStart = new Date(),
            types = event_types.length,
            chart_series,
            i;

        chart_series = [];
        for (i = 0; i < types; i += 1) {
            chart_series.push({
                type: 'column',
                name: event_types[i] + ' Events',
                data: []
            });
        }

        chart_series.push({
            type: 'spline',
            name: 'Event Sum',
            yAxis: 1,
            data: []
        });

        chart_config.series = chart_series;

        chart = new Highcharts.Chart(chart_config);

        pointStart.setDate(pointStart.getDate() - 2);
        pointStart.setSeconds(0);
        pointStart.setMilliseconds(0);

        $.ajax({
            url: url_base + 'begin=' +  moment.utc(pointStart).toISOString(),
            dataType: 'json',
            success: function (data) {
                var series = [],
                    t_start = pointStart.getTime(),
                    cummulative = [],
                    rate = [],
                    total = 0,
                    sum = 0,
                    t,
                    i;

                for (i = 0; i < types; i += 1) {
                    sum = 0;
                    series.push([]);
                    $.each(data[event_types[i]].points, function (ii) {
                        t = t_start + (ii * 60 * 1000);
                        total += this;
                        sum += this;
                        series[i].push([t, this]);

                        if (ii < cummulative.length) {
                            cummulative[ii][1] += sum;
                            rate[ii].y += this;
                        }
                        else {
                            cummulative.push([t, sum]);
                            rate.push({x: t, y: this});
                        }
                    });

                    chart.series[i].setData(series[i], true);
                }

                $('#event-count').html(total);
                chart.series[types].setData(cummulative, true);
                updateGauge(rate);
            },
            error: function (xhr) {
                var json;
                try {
                    json = $.parseJSON(xhr.responseText);
                    console.log('Event service error:' + json.error);
                } catch (e) {
                    console.log('Unknown event service error');
                }
            }
        });

        if ($('.import-health').length) {
            $('p.import-update > span + a').on('click', function () {
                stopImportMonitoring();
                startImportMonitoring();
            });
        }
    }

    if ($('.course-filter').length) {
        initializeSearchForm();
    }

    initializeCourseListEvents();

    if ($('.import-health').length) {
        initializeStripAndGauge(['enrollment', 'instructor']);
        initializeImportEvents();
        startImportMonitoring();
        startCanvasStatusMonitor();
        startTermDatesMonitor();
    } else if ($('#group-table').length) {
        initializeStripAndGauge(['group']);
        loadGroups();
    } else if ($('#user-search').length) {
        initializeStripAndGauge(['person']);
        initializeUserSearchEvents();
    } else if ($('#admin-table').length) {
        loadAdmins();
    } else if ($('#jobs-table').length) {
        loadJobs();
        setInterval(reLoadJobs, 5 * 1000);
    }
});
