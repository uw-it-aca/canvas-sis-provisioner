from uw_gws.models import GroupMember
import xml.etree.ElementTree as ET
import re


class ExtractUpdate(Extract):
    def parse(self, content_type, body):
        # normalize 'update-members' event
        if content_type == 'xml':
            rx = re.compile(r'^(<.*>)[^>]*$')
            root = ET.fromstring(rx.sub(r'\g<1>', body))
            event = {
                'group_id': root.findall('./name')[0].text,
                'reg_id': root.findall('./regid')[0].text,
                'add_members': [],
                'delete_members': [],
            }
            for member in root.findall('./add-members/add-member'):
                event['add_members'].append(
                    GroupMember(name=member.text, type=member.attrib['type']))

            for member in root.findall('./delete-members/delete-member'):
                event['delete_members'].append(
                    GroupMember(name=member.text, type=member.attrib['type']))

            return event

        raise ExtractException('Unknown event content-type: {}'.format(
            content_type))


class ExtractDelete(Extract):
    def parse(self, content_type, body):
        # body contains group identity information
        # normalize 'delete-group' event
        if content_type == 'xml':
            rx = re.compile(r'^(<.*>)[^>]*$')
            root = ET.fromstring(rx.sub(r'\g<1>', body))
            return {
                'group_id': root.findall('./name')[0].text,
                'reg_id': root.findall('./regid')[0].text
            }
        raise ExtractException('Unknown delete event content-type: {}'.format(
            content_type))


class ExtractChange(Extract):
    def parse(self, content_type, body):
        # body contains old and new subject names (id)
        # normalize 'change-subject-name' event
        if content_type == 'xml':
            rx = re.compile(r'^(<.*>)[^>]*$')
            root = ET.fromstring(rx.sub(r'\g<1>', body))
            return {
                'old_name': root.findall('./subject/old-name')[0].text,
                'new_name': root.findall('./subject/new-name')[0].text
            }

        raise ExtractException('Unknown delete event content-type: {}'.format(
            content_type))
