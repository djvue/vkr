import requests


timeout = 240


def batch_get_rewards(completions, project_path, relative_package_path, relative_file_path) -> list[float]:
    # print({
    #         'completions': completions,
    #         'project_path': project_path,
    #         'relative_package_path': relative_package_path,
    #         'relative_file_path': relative_file_path,
    #     })

    for i in range(5):
        scores = []
        try:
            resp = requests.post('http://91.122.220.250:46800/score', json={
                'completions': completions,
                'project_path': project_path,
                'relative_package_path': relative_package_path,
                'relative_file_path': relative_file_path,
            }, headers={'Content-type': 'application/json'}, timeout=timeout)

            if resp.status_code != 200:
                continue

            scores = resp.json()['scores']
        except Exception:
            continue

        return scores

    return [0.0]*len(completions)

