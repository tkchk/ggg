"""
The whole point of this script is to find a host in zabbix and create both simple web check and corresponding trigger
if the response code is higher than 400 representing an error.
It's not much of a user friendly - it's not accepting any arguments. It should be modified beforehand.
"""

from pyzabbix import ZabbixAPI
import sys
import logging

class ZabbixWebCheckCreator:
    def __init__(self, server_url, username, password):
        self.zapi = ZabbixAPI(server_url)
        self.zapi.login(username, password)
        logging.info(f"Connected to Zabbix API Version {self.zapi.api_version()}")

    def create_web_scenario(self, host_id, scenario_name, url):
        try:
            steps = [{
                "name": "Main page",
                "url": url,
                "follow_redirects": 0,
                "no": 1  # Step number
            }]

            scenario = {
                "hostid": host_id,
                "name": scenario_name,
                "steps": steps,
                "retries": 1,
            }

            result = self.zapi.httptest.create(**scenario)
            logging.info(f"Created web scenario '{scenario_name}' with ID {result['httptestids'][0]}")
            return result['httptestids'][0]
        except Exception as e:
            logging.error(f"Failed to create web scenario: {e}")
            return None

    def create_trigger(self, host_id, scenario_name):
        try:
            triggers = [
                {
                    "description": f"{scenario_name} response code",
                    "comments": f"Web scenario {scenario_name} failed: {{ITEM.VALUE}}",
                    "expression": f"last(/Zabbix server/web.test.rspcode[{scenario_name},Main page])>400",
                    "priority": 4,  # High priority
                    "tags": [{"tag": "web", "value": "true"}]
                }
            ]

            trigger_ids = []
            for trigger in triggers:
                result = self.zapi.trigger.create(**trigger)
                trigger_ids.append(result["triggerids"][0])
                logging.info(f"Created trigger '{trigger['description']}' with ID {result['triggerids'][0]}")

            return trigger_ids
        except Exception as e:
            logging.error(f"Failed to create triggers: {e}")
            return None

    def get_host_by_name(self, hostname):
        try:
            result = self.zapi.host.get(filter={"host": hostname})
            if result:
                return result[0]["hostid"]
            return None
        except Exception as e:
            logging.error(f"Failed to get host: {e}")
            return None

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Zabbix connection details
    ZABBIX_SERVER = 'http://zabbix.local'
    ZABBIX_USER = 'user'
    ZABBIX_PASSWORD = 'password'

    creator = ZabbixWebCheckCreator(ZABBIX_SERVER, ZABBIX_USER, ZABBIX_PASSWORD)

    web_checks = [
        {
            "hostname": "Zabbix server",
            "scenario_name": "sample.local",
            "url": "http://sample.local"
        }
    ]

    for check in web_checks:
        # Get host ID
        host_id = creator.get_host_by_name(check["hostname"])
        if not host_id:
            logging.error(f"Host {check['hostname']} not found")
            continue

        # Create web scenario
        scenario_id = creator.create_web_scenario(
            host_id,
            check["scenario_name"],
            check["url"]
        )

        if scenario_id:
            # Create triggers
            creator.create_trigger(host_id, check["scenario_name"])

if __name__ == "__main__":
    main()
