# moved github_branch_protection
moved {
  from = module.ministryofjustice.module.cloud-optimisation-and-accountability.github_branch_protection.default
  to   = module.github-repository.module.cloud-optimisation-and-accountability.github_branch_protection.default
}

# moved github_repository
moved {
  from = module.ministryofjustice.module.cloud-optimisation-and-accountability.github_repository.default
  to   = module.github-repository.module.cloud-optimisation-and-accountability.github_repository.default
}

# moved github_team_repository
moved {
  from = module.ministryofjustice.module.cloud-optimisation-and-accountability.github_team_repository.admin["12623342"]
  to   = module.github-repository.module.cloud-optimisation-and-accountability.github_team_repository.admin["12623342"]
}

# moved github_branch_protection
moved {
  from = module.ministryofjustice.module.coat-cur-data-pipeline.github_branch_protection.default
  to   = module.github-repository.module.coat-cur-data-pipeline.github_branch_protection.default
}

# moved github_repository
moved {
  from = module.ministryofjustice.module.coat-cur-data-pipeline.github_repository.default
  to   = module.github-repository.module.coat-cur-data-pipeline.github_repository.default
}

# moved github_team_repository
moved {
  from = module.ministryofjustice.module.coat-cur-data-pipeline.github_team_repository.admin["12623342"]
  to   = module.github-repository.module.coat-cur-data-pipeline.github_team_repository.admin["12623342"]
}
