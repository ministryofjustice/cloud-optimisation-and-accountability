# moved github_branch_protection
moved {
  from = module.ministryofjustice-new.module.cloud-optimisation-and-accountability-new.github_branch_protection.default
  to   = module.cloud-optimisation-and-accountability.github_branch_protection.default
}

# moved github_repository
moved {
  from = module.ministryofjustice-new.module.cloud-optimisation-and-accountability-new.github_repository.default
  to   = module.cloud-optimisation-and-accountability.github_repository.default
}

# moved github_team_repository
moved {
  from = module.ministryofjustice-new.module.cloud-optimisation-and-accountability-new.github_team_repository.admin["12623342"]
  to   = module.cloud-optimisation-and-accountability.github_team_repository.admin["12623342"]
}

# moved github_branch_protection
moved {
  from = module.ministryofjustice-new.module.coat-cur-data-pipeline-new.github_branch_protection.default
  to   = module.coat-cur-data-pipeline.github_branch_protection.default
}

# moved github_repository
moved {
  from = module.ministryofjustice-new.module.coat-cur-data-pipeline-new.github_repository.default
  to   = module.coat-cur-data-pipeline.github_repository.default
}

# moved github_team_repository
moved {
  from = module.ministryofjustice-new.module.coat-cur-data-pipeline-new.github_team_repository.admin["12623342"]
  to   = module.coat-cur-data-pipeline.github_team_repository.admin["12623342"]
}
