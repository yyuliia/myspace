from jira import JIRA
import re
import logging


class JiraSource:

    def __init__(self, user_name, password, ticket, server='https://atlassian.spscommerce.com'):
        self.user_name = user_name
        self.password = password
        self.ticket = ticket
        self.server = server

    def jira_auth(self):
        options = {'server': self.server}
        jira = JIRA(options, basic_auth=(self.user_name, self.password))
        if jira:
            return jira
        else:
            logging.INFO("Failed connection")

    def isa_gs_ids_pattern(self, identifiers):
        try:
            identifiers = str(identifiers).replace(" ", "").replace("*", "/")
            if re.match(r'(\d{2}|\w{2})/.(\d+|\w+)/.(\d+|\w+)', identifiers):
                envelop_qualifier = re.search(r'(\d{2}|\w{2})/', identifiers).group()[:-1]
                envelope_id = re.search(r'/.+/', identifiers).group()[1:-1]
                group_id = re.search(r'/.(\d+\w+|(\w+\d+)|\d+|\w+)', identifiers).group()[1:]
                return envelop_qualifier.strip(), envelope_id.strip(), group_id.strip()

            elif re.match(r'(\d{2}|\w{2})/.(\d+|\w+)', identifiers):
                envelop_qualifier = re.search(r'(\d{2}|\w{2})/', identifiers).group()[:-1]
                envelope_id = re.search(r'/.+', identifiers).group()[1:]
                group_id = envelope_id
                return envelop_qualifier.strip(), envelope_id.strip(), group_id.strip()
            elif re.match(r'(\d{2}|\w{2})$', identifiers):
                envelop_qualifier = re.search(r'(\d{2}|\w{2})', identifiers).group()
                envelope_id = 'N/A'
                group_id = 'N/A'
                return envelop_qualifier.strip(), envelope_id.strip(), group_id.strip()
            elif re.match(r'.(\d+|\w+)', identifiers):
                envelop_qualifier = 'N/A'
                envelope_id = re.search(r'.(\d+|\w+)', identifiers).group()
                group_id = 'N/A'
                return envelop_qualifier.strip(), envelope_id.strip(), group_id.strip()
            else:
                return ['N/A', ] * 3
        except TypeError:
            logging.error("Type Error")

    def find_fields_main_task(self):
        gathered_jira_data = {}
        jira = self.jira_auth()
        short_ticket = re.search(r'\w{2}-.+', self.ticket).group()
        issue = jira.issue(short_ticket)

        if issue.fields.customfield_10208:
            gathered_jira_data['HubCompanyName'] = issue.fields.customfield_10208
        else:
            gathered_jira_data['HubCompanyName'] = 'N/A'
        if issue.fields.customfield_10316:
            gathered_jira_data['HubID'] = issue.fields.customfield_10316
        else:
            gathered_jira_data['HubID'] = 'N/A'

        try:
            edi_ids = self.isa_gs_ids_pattern(issue.fields.customfield_11501)
            gathered_jira_data['EnvelopQualifier'] = edi_ids[0]
            gathered_jira_data['EnvelopeID'] = edi_ids[1]
            gathered_jira_data['GroupID'] = edi_ids[2]
        except TypeError:
            logging.error("There is missing information")

        if issue.fields.description:
            try:
                version = re.search(r'Version:.(\d+|\W\d{2}\W)', issue.fields.description).group()[8:]
                if version:
                    gathered_jira_data['EDIVersion'] = version.strip()
            except AttributeError:
                gathered_jira_data['EDIVersion'] = 'N/A'

        if issue.fields.subtasks:
            info_sub_tasks = []
            gathered_ecs_task = {}

            for item in issue.fields.subtasks:
                gathered_sub_task = {}
                sub_issue = jira.issue(item.key)
                if ('Platform Admin / TOMMM Task' not in sub_issue.fields.summary) \
                        and ('AS2' not in sub_issue.fields.summary) \
                        and ('FTP' not in sub_issue.fields.summary):
                    if ('ECS' not in sub_issue.fields.summary) and ('ecs' not in sub_issue.fields.summary):
                        document_number = sub_issue.fields.customfield_31714
                        other_document = re.findall(r'Other', str(document_number))
                        if document_number and other_document is None:
                            edi_doc = (str(document_number)[(str(document_number)).index("value='") +
                                                            7:(str(document_number)).index("value='") + 10])
                            edifact_doc = (str(document_number)[(str(document_number)).index("value='")
                                                                + 7:(str(document_number)).index("value='") + 13])
                            if re.findall(r'\d{3}', edi_doc):
                                gathered_sub_task['DocumentNumber'] = edi_doc
                            else:
                                gathered_sub_task['DocumentNumber'] = edifact_doc

                        else:
                            document_number = re.search(r'\d{3}|[A-Z]{6}', sub_issue.fields.summary)
                            if document_number:
                                gathered_sub_task['DocumentNumber'] = document_number.group()
                            else:
                                continue
                        if sub_issue.fields.customfield_10211:
                            gathered_sub_task['RetailerMapName'] = sub_issue.fields.customfield_10211
                        else:
                            gathered_sub_task['RetailerMapName'] = 'N/A'
                        info_sub_tasks.append(gathered_sub_task)
                    else:
                        ecs_doc_number = sub_issue.fields.customfield_31714
                        ecs_other_document = re.findall(r'Other', str(ecs_doc_number))
                        ecs_document_number = ''
                        if ecs_doc_number and ecs_other_document is None:
                            ecs_tpd_document_number_EDI = (
                                str(ecs_doc_number)[(str(ecs_doc_number)).index("value='") +
                                                    7:(str(ecs_doc_number)).index("value='") + 10])
                            ecs_tpd_document_number_EDIFACT = (
                                str(ecs_doc_number)[(str(ecs_doc_number)).index("value='") +
                                                    7:(str(ecs_doc_number)).index("value='") + 13])
                            if ecs_tpd_document_number_EDI:
                                ecs_document_number = ecs_tpd_document_number_EDI
                            else:
                                ecs_document_number = ecs_tpd_document_number_EDIFACT

                        else:
                            ecs_summary_doc_number = re.search(r'\d{3}|[A-Z]{6}', sub_issue.fields.summary)
                            if ecs_summary_doc_number:
                                ecs_document_number = ecs_summary_doc_number.group()

                        if ecs_document_number and sub_issue.fields.customfield_10211 is not None:
                            gathered_ecs_task[ecs_document_number] = sub_issue.fields.customfield_10211
                        elif sub_issue.fields.customfield_10211 is not None:
                            gathered_ecs_task['N/A'] = sub_issue.fields.customfield_10211
                        else:
                            gathered_ecs_task[ecs_document_number] = 'N/A'

            if gathered_ecs_task:
                for data in range(len(info_sub_tasks)):
                    for key in gathered_ecs_task:
                        if info_sub_tasks[data].get('DocumentNumber') == key:
                            info_sub_tasks[data]['ECS'] = gathered_ecs_task.get(key)
            gathered_jira_data['SubTask'] = info_sub_tasks

        return gathered_jira_data