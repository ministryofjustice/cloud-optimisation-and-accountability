module "cloud-optimisation-and-accountability" {
  source = "../../modules/github-repository"

  poc = false

  name        = "terraform-github-repository"
  description = "A GitHub repository for the Cloud Optimisation and Accountability Team"
  topics      = ["cloud-optimisation-and-accountability"]

  homepage_url = "https://github.com/ministryofjustice/terraform-github-repository"

  team_access = {
    admin = [var.cloud_optimisation_and_accountability_team_id]
  }
}
