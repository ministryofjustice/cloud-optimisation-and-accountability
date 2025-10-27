# Cloud Optimisation and Accountability

[![Ministry of Justice Repository Compliance Badge](https://github-community.service.justice.gov.uk/repository-standards/api/cloud-optimisation-and-accountability/badge)](https://github-community.service.justice.gov.uk/repository-standards/cloud-optimisation-and-accountability)

Welcome to the Cloud Optimisation and Accountability Team (🧥COAT) mono-repo. This repository contains all code relating to COAT activities.

## Cloud Optimisation and Accountability Website

The [Cloud Optimisation and Accountability website](https://cloud-optimisation-and-accountability.justice.gov.uk/) contains user guides and runbooks for services and tools provided by the Cloud Optimisation and Accountability Team.

The website is based on the Ministry of Justice's [template-documentation-site](https://github.com/ministryofjustice/template-documentation-site).

### Running locally

To run the website locally use:

```sh
make preview
```

Then view the website at <http://localhost:4567>.

### Updating documentation

Update documentation by editing any of the `*.html.md.erb` files under
the [source/documentation](source/documentation) sub-directories.

The syntax used in `*.html.md.erb` is Markdown, though it also supports some
GOV.UK Design System specifics, as listed at [Tech Docs Template - Write your
content](https://github.com/alphagov/tdt-documentation/blob/main/source/write_docs/content/index.html.md.erb).

### Publishing changes

Any changes that are merged into the `main` branch will be published
automatically through the [`publish.yml` GitHub action](.github/workflows/publish.yml).

The website is hosted on [GitHub Pages](https://pages.github.com/).

### Configuring the website

#### Global configuration

The [GOV.UK Tech Docs Template global configuration options](https://github.com/alphagov/tdt-documentation/blob/main/source/configure_project/global_configuration/index.html.md.erb)
can be used in this repository to configure the Cloud Optimisation and Accoutability Team user guides.

#### Structuring documentation and page configuration

The [GOV.UK Tech Docs Template "Configure your documentation project"](https://github.com/alphagov/tdt-documentation/blob/main/source/configure_project/index.html.md.erb)
offers a range of guidance regarding configuration options to help structure
documentation and configure pages separately.
