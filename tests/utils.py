import json
import os
from enum import Enum, auto
from typing import Any, Dict, Union

from asgard.conf import settings

CURRENT_DIR = os.path.dirname(__file__)
FIXTURES_PATH = os.path.join(CURRENT_DIR, "fixtures")


class ClusterOptions(Enum):
    CONNECTION_ERROR = auto()
    ADD_APPS_FROM_FIXTURE = auto()
    DO_NOT_ADD = auto()


def get_fixture(file_name: str) -> Dict:
    with open(os.path.join(FIXTURES_PATH, file_name)) as fp:
        return json.load(fp)


def get_raw_fixture(file_name: str) -> Dict:
    with open(os.path.join(FIXTURES_PATH, file_name)) as fp:
        return fp.read()


def with_json_fixture(fixture_path):
    def wrapper(func):
        def decorator(self, *args):
            fixture = get_fixture(fixture_path)
            return func(self, *args, fixture)

        return decorator

    return wrapper


def add_agent_running_tasks(rsps, agent_id, agent_apps):
    agent_info = get_fixture(f"agents/{agent_id}/info.json")
    agent_containers = get_fixture(f"agents/{agent_id}/containers.json")
    if agent_apps == ClusterOptions.ADD_APPS_FROM_FIXTURE:
        rsps.get(
            f"http://{agent_info['hostname']}:{agent_info['port']}/containers",
            payload=agent_containers,
            status=200,
        )
    if agent_apps == ClusterOptions.CONNECTION_ERROR:
        rsps.get(
            f"http://{agent_info['hostname']}:{agent_info['port']}/containers",
            exception=ConnectionError(),
            status=200,
        )


def add_agent_task_stats(rsps, agent_id, index_name):
    task_stats_datapoints = get_fixture(f"agents/{agent_id}/app_stats.json")
    task_stats_aggr = get_fixture(
        f"agents/{agent_id}/app_stats_aggr_results.json"
    )
    app_name = task_stats_datapoints[0]["appname"].strip("/")
    app_name_for_index_path = app_name.replace("/", "-")
    url = f"{settings.STATS_API_URL}/{index_name}/_search"
    data = {
        "took": 325,
        "timed_out": False,
        "_shards": {"total": 240, "successful": 240, "failed": 0},
        "hits": {
            "total": 1_015_808,
            "max_score": 1,
            "hits": task_stats_datapoints,
        },
        "aggregations": task_stats_aggr,
    }
    rsps.get(url, payload=data, status=200)


def build_mesos_cluster(rsps, *agent_configs: Union[Dict[str, Any], str]):
    """
    Cria as chamadas necessárias no aioresponses para que um cluster de mesos
    exista com os agents escolhidos. Dos dados de cada agent estão em `tests/fixtures/agents/<agent_id>/*`.

    Quando o agent_config é um dict, possui o seguinte formato:
        {
            "id": Id do agent desejado
            "apps": Uma das opções co enum tests.utils.ClusterOptions
        }

        se a chave "apps" não existir será escolhida a opção `ClusterOptions.ADD_APPS_FROM_FIXTURE`

    """
    all_agents_info = []
    rsps.get(
        f"{settings.MESOS_API_URLS[0]}/redirect",
        status=301,
        headers={"Location": settings.MESOS_API_URLS[0]},
    )

    for mesos_master_url in settings.MESOS_API_URLS:
        rsps.get(
            f"{mesos_master_url}/redirect",
            status=301,
            headers={"Location": settings.MESOS_API_URLS[0]},
        )

    for agent_config in agent_configs:
        if isinstance(agent_config, str):
            agent_id = agent_config
            agent_apps = ClusterOptions.ADD_APPS_FROM_FIXTURE
        elif isinstance(agent_config, dict):
            agent_id = agent_config["id"]
            agent_apps = agent_config.get(
                "apps", ClusterOptions.ADD_APPS_FROM_FIXTURE
            )

        agent_info = get_fixture(f"agents/{agent_id}/info.json")
        all_agents_info.append(agent_info)
        add_agent_running_tasks(rsps, agent_id, agent_apps)
        rsps.get(
            f"{settings.MESOS_API_URLS[0]}/slaves?slave_id={agent_id}",
            payload={"slaves": [agent_info]},
            status=200,
        )
        rsps.get(
            f"{settings.MESOS_API_URLS[0]}/slaves?slave_id={agent_id}",
            payload={"slaves": [agent_info]},
            status=200,
        )

    rsps.get(
        f"{settings.MESOS_API_URLS[0]}/slaves",
        payload={"slaves": all_agents_info},
        status=200,
    )
