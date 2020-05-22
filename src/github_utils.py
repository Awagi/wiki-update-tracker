from constants import GITHUB_URL


def file_url(repo_name, rev, path):
    """
    Forges Github URL to a blob in a repo (through branch or commit rev).

    :param repo_name: Github repository name such as 'Author/Repo'
    :param rev: branch, commit or tag
    :param path: the path to the file
    :return: URL type str
    """
    return "{}/{}/blob/{}/{}".format(GITHUB_URL, repo_name, rev, path)


def raw_file_url(repo_name, rev, path):
    """
    Forges Github URL to a blob raw content in a repo (through branch or commit rev).

    :param repo_name: Github repository name such as 'Author/Repo'
    :param rev: branch, commit or tag
    :param path: the path to the file
    :return: URL type str
    """
    return "{}/{}/raw/{}/{}".format(GITHUB_URL, repo_name, rev, path)


def compare_url(repo_name, rev_a, rev_b):
    """
    Forges Github URL to compare rev_a to rev_b with link to files comparison.

    :param repo_name: Github repository name such as 'Author/Repo'
    :param rev_a: branch, commit or tag
    :param rev_b: branch, commit or tag
    :return: URL type str
    """
    return "{}/{}/compare/{}...{}#files_bucket".format(GITHUB_URL, repo_name, rev_a, rev_b)

