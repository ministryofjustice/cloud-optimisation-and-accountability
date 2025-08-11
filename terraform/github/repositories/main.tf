locals {

  cloud_optimisation_and_accountability_team_id = data.github_team.cloud_optimisation_and_accountability.id

}

#cloud-optimisation-and-accountability
module "cloud-optimisation-and-accountability" {
  source = "../modules/github-repository"

  poc = false

  name        = "cloud-optimisation-and-accountability"
  description = "A GitHub repository for the Cloud Optimisation and Accountability Team"
  topics      = ["cloud-optimisation-and-accountability"]

  homepage_url = "https://cloud-optimisation-and-accountability.justice.gov.uk/"

  team_access = {
    admin = [local.cloud_optimisation_and_accountability_team_id]
  }
}

#coat-cur-data-pipeline
module "coat-cur-data-pipeline" {
  source = "../modules/github-repository"


  poc = false

  name        = "coat-cur-data-pipeline"
  description = "A GitHub repository for the Cloud Optimisation and Accountability Team Cost and Usage Report Data Pipeline "
  topics      = ["cloud-optimisation-and-accountability"]

  homepage_url = "https://cloud-optimisation-and-accountability.justice.gov.uk/"

  team_access = {
    admin = [local.cloud_optimisation_and_accountability_team_id]
  }

  template = {
    "owner" : "ministryofjustice",
    "repository" : "analytical-platform-airflow-python-template"
  }
}
