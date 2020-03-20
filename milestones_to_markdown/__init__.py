import os
from random import choice
from argparse import ArgumentParser, FileType


from github import Github


try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass


def print_markdown(repository):
    milestones = repository.get_milestones()
    labels = repository.get_labels()

    seen_issues = set()

    lines = []

    for milestone in milestones:
        lines.append(f"# {milestone.title}")
        lines.append(f"**ETA {milestone.due_on}**")

        lines.append("")
        lines.append(milestone.description)
        lines.append("")

        for label in labels:
            issues = repository.get_issues(milestone=milestone, labels=[label])

            if issues.totalCount > 0:

                if label.description:
                    lines.append(f"* {label.name} - {label.description}")
                else:
                    lines.append(f"* {label.name}")

                for issue in issues:
                    if issue.id in seen_issues:
                        continue

                    seen_issues.add(issue.id)

                    labels = issue.labels

                    if issue.state == 'open':
                        lines.append(f"  * {issue.title} [Github Issue #{issue.number}]({issue.html_url})")
                    else:
                        lines.append(f"  * ~~{issue.title} [Github Issue #{issue.number}]({issue.html_url})~~")

        lines.append("")

    lines.append("---")
    lines.append(f"For more information see [the Repository that this Roadmap was generated from.]({repository.html_url})")

    return '\n'.join(lines)


def cli():
    parser = ArgumentParser()

    parser.add_argument('--github-token', type=str, default=os.environ.get('GITHUB_TOKEN'))
    parser.add_argument('--output-file', type=FileType('w'))
    parser.add_argument('repository', type=str)

    args = parser.parse_args()

    token = args.github_token
    repository = args.repository
    output_file = args.output_file

    markdown = print_markdown(Github(token).get_repo(repository))

    if output_file:
        output_file.write(markdown)
    else:
        print(markdown)


if __name__ == "__main__":
    cli()
