import os
import re
from argparse import ArgumentParser, FileType
from collections import defaultdict
from urllib.parse import urlparse, urlunparse

from github import Github, Project


try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass


def get_milestone_html_url(milestone):
    milestone_api_url = milestone.url

    milestone_api_path = urlparse(milestone_api_url).path

    matches = re.match(r'/repos/([^/]+)/([^/]+)/milestones/(\d+)', milestone_api_path)

    org, repo, number = matches.groups()

    milestone_path = f"{org}/{repo}/milestone/{number}"

    return urlunparse(('https', 'github.com', milestone_path, '', '', ''))


def get_card_content(card):
    # We can't use lru_cache here because `card` is not hashable.
    # Unfortunately.
    # In place of that we're just using a memoization off of the
    # function called.  It's hacky but.. well, better than nothing, right?

    if not hasattr(get_card_content, '_card_content_memo'):
        setattr(get_card_content, '_card_content_memo', {})
    memo = getattr(get_card_content, '_card_content_memo')

    if card.id not in memo:
        try:
            memo[card.id] = card.get_content()
        except:
            memo[card.id] = None

    return memo.get(card.id, None)


def format_card(card):
    content = get_card_content(card)

    if content:
        line = f"{content.title} - [Issue #{content.number}]({content.html_url})"

        if content.state == "closed":
            line = f"~~{line}~~"
    else:
        line = card.note

    line = f"{line}".strip()

    if not line:
        return None

    line = line.replace("\n", " ")

    return f"* {line}"


def format_cards(cards):
    return list(filter(None, [format_card(card) for card in cards]))


def project_to_markdown(project : Project) -> str:
    # For every column in the project we want to print out:
    # * Milestones in order of appearance and the cards within in the order of appearance.
    # * Non-milestone cards in order of appearance

    lines = []

    body = project.body

    # We've wrapped stuff in CDATA to prevent it from messing up the github pages.
    # If there's anything that's CDATA let's pull it outta there.
    body = re.sub(r'<!\[CDATA\[(.*?)\]\]>', '\g<1>', body, flags=re.MULTILINE | re.DOTALL)

    lines.extend(body.strip().split("\n"))

    lines.append("")
    lines.append("---")

    for column in project.get_columns():
        lines.append(f"# {column.name}")

        cards_by_milestone = defaultdict(lambda: [])

        milestones = []

        # We first want to index every card by milestone
        # while retaining the order.
        for card in column.get_cards():
            content = get_card_content(card)

            milestone_id = None

            if content:
                milestone = content.milestone

                if milestone:
                    if milestone not in milestones:
                        milestones.append(milestone)
                    milestone_id = milestone.id

            cards_by_milestone[milestone_id].append(card)

        # Now for each of the milestones we want to pull related cards.
        for milestone in milestones:
            milestone_cards = cards_by_milestone.get(milestone.id)

            milestone_url = get_milestone_html_url(milestone)

            lines.append(f"## [{milestone.title}]({milestone_url})")

            if milestone.due_on:
                eta = milestone.due_on.date().isoformat()

                lines.append(f"**ETA {eta}**")
                lines.append("")

            if milestone.description:
                lines.extend(milestone.description.split("\n"))

            lines.append("")
            lines.extend(format_cards(milestone_cards))
            lines.append("")

        # Place non-milestone related cards later.
        if None in cards_by_milestone:
            lines.append("## Miscellaneous Tasks")
            lines.append("These tasks have no product features or milestones associated with them.")

            lines.append("")
            lines.extend(format_cards(cards_by_milestone.pop(None)))
            lines.append("")

    lines.append("---")
    lines.append(f"For more information see [the Project that this Roadmap was generated from.]({project.html_url})")

    return '\n'.join(lines)


def get_project(github : Github, uri : str) -> Project:
    project_selector = {}
    project_path = urlparse(uri).path

    if matches := re.match(r'^/orgs/([^/]+)/projects/(\d+)$', project_path):
        # https://github.com/orgs/common-room/projects/1
        projects = github.get_organization(matches.group(1)).get_projects()
        project_selector['number'] = int(matches.group(2))
    elif matches := re.match(r'^/([^/]+/[^/]+)/projects/(\d+)$', project_path):
        # https://github.com/common-room/architecture-docs/projects/1
        projects = github.get_repo(matches.group(1)).get_projects()
        project_selector['number'] = int(matches.group(2))

    # First search for the project by number..
    for project in projects:
        if all([getattr(project, key, None) == value  for key, value in project_selector.items()]):
            return project

    raise ValueError(f"Project not found")


def cli():
    parser = ArgumentParser()

    parser.add_argument('--github-token', type=str, default=os.environ.get('GITHUB_TOKEN'))
    parser.add_argument('--output-file', type=FileType('w'))
    parser.add_argument('project_uri')

    args = parser.parse_args()

    token = args.github_token
    output_file = args.output_file
    project_uri = args.project_uri

    github = Github(token)

    project = get_project(github, project_uri)

    markdown = project_to_markdown(project)

    if output_file:
        output_file.write(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    cli()
