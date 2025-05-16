import requests


timeout = 240


def batch_get_rewards(completions, project_path, relative_go_package, func_name) -> list[float]:
    # print({
    #         'completions': completions,
    #         'project_path': project_path,
    #         'relative_go_package': relative_go_package,
    #         'func_name': func_name,
    #     })

    for i in range(5):
        scores = []
        try:
            resp = requests.post('http://91.122.220.250:46800/score', json={
                'completions': completions,
                'project_path': project_path,
                'relative_go_package': relative_go_package,
                'func_name': func_name,
            }, headers={'Content-type': 'application/json'}, timeout=timeout)

            if resp.status_code != 200:
                continue

            scores = resp.json()['scores']
        except Exception:
            continue

        return scores

    return [0.0]*len(completions)

