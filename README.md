# Caliban

![](https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg)

> “Be not afeard; the isle is full of noises,
> Sounds, and sweet airs, that give delight and hurt not.
> Sometimes a thousand twangling instruments
> Will hum about mine ears; and sometime voices,
> That, if I then had waked after long sleep,
> Will make me sleep again: and then, in dreaming,
> The clouds methought would open, and show riches
> Ready to drop upon me; that, when I waked,
> I cried to dream again.”
>
> -- <cite>Shakespeare, The Tempest</cite>

## Overview

Caliban is a tool for running python code inside of Docker containers, then
submitting those containers up to Cloud.

## Prerequisites

Before you run anything you need a solid Cloud and Docker installation.

- environment variables we use

## Getting Caliban

How to install using pipx.

## Using Caliban

If you want to practice, go to Hello World. Read below for information on the
specific commands exposed by Caliban.

### caliban shell

### caliban run

### caliban cloud

## Contributing

To push code,

First run this:

```sh
f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f) ; curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x $f
```

- create a branch
- work!
- commit
- `git push origin HEAD:refs/for/master`

More info to file on the process: https://www.gerritcodereview.com/user-review-ui.html

And info from internally on how code review works: https://g3doc.corp.google.com/company/teams/gerritcodereview/users/intro-codelab.md?cl=head#create-a-change

## Testing

This is how to configure tests.

https://g3doc.corp.google.com/devtools/kokoro/g3doc/userdocs/general/gob_scm.md?cl=head

# Trouble?

Get in touch with samritchie@google.com.
