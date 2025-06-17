# Cloud Optimisation and Accountability

This repository holds the website runbooks for services and tools provided by the Cloud Optimisation and Accountability Team [Cloud Optimisation and Accountability](Add URL)

This repository utilises the Ministry of Justice's [template-documentation-site](https://github.com/ministryofjustice/template-documentation-site).

> Want to give feedback on the documentation? [Open an issue on this repository](https://github.com/ministryofjustice/cloud-optimisation-and-accountability/issues).

## Running locally

You can run this website locally by running:

```sh
make preview
```

You can then browse to <http://localhost:4567> to view the website.

## Updating documentation

You can update the documentation by editing any of the `*.html.md.erb` files in
the [source](source) directory.

The syntax used in `*.html.md.erb` is Markdown, though it also supports some
GOV.UK Design System specifics, as listed on [Tech Docs Template - Write your
content](https://github.com/alphagov/tdt-documentation/blob/main/source/write_docs/content/index.html.md.erb).

## Publishing changes

Any changes that are merged into the `main` branch will be published
automatically through the [`publish.yml` GitHub action](.github/workflows/publish.yml).

This website is hosted on [GitHub Pages](https://pages.github.com/).

## Configuring the website

### Global configuration

The [GOV.UK Tech Docs Template global configuration options](https://github.com/alphagov/tdt-documentation/blob/main/source/configure_project/global_configuration/index.html.md.erb)
can be used in this repository to configure the Operations Engineering user guides.

### Structuring documentation and page configuration

The [GOV.UK Tech Docs Template "Configure your documentation project"](https://github.com/alphagov/tdt-documentation/blob/main/source/configure_project/index.html.md.erb)
offers a range of guidance regarding configuration options to help structure
documentation and configure pages separately.
