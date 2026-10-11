# API Reference

## Client

::: pyhyves.Pyhyves
    options:
      filters: ['!^_', '__\w+__$']

### Inloggegevens

::: pyhyves.PasswordCredentials
    options:
      filters: ['!^_', '__\w+__$']

::: pyhyves.TokenCredentials
    options:
      filters: ['!^_', '__\w+__$']

## Types

::: pyhyves.AccountId

::: pyhyves.GroupId

::: pyhyves.PostId

::: pyhyves.CommentId

::: pyhyves.KEEP_CURRENT
    options:
      filters: ['!^_', '__\w+__$']

## Exceptions

::: pyhyves.HyvesAPIException

::: pyhyves.HyvesAuthException

## Accounts

::: pyhyves.AccountRef

::: pyhyves.AccountPreview

::: pyhyves.BaseAccount

::: pyhyves.Account

::: pyhyves.ClientAccount

## Hyves

::: pyhyves.GroupRef

::: pyhyves.GroupPreview

::: pyhyves.Group

::: pyhyves.GroupRole

::: pyhyves.GroupVisibility

::: pyhyves.GroupMember

::: pyhyves.GroupUserOptions
    options:
      filters: ['!^_', '__\w+__$']

## Posts

::: pyhyves.PostRef

::: pyhyves.BasePost

::: pyhyves.GroupPost

::: pyhyves.WallPost

::: pyhyves.TimelinePost

::: pyhyves.Post

::: pyhyves.PostType

### Reacties

::: pyhyves.Comment