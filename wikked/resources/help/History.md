
Every time you edit a page, Wikked stores a new _revision_ of the page. The
series of revisions, going all the way back to the creation of a page,
constitute the _history_ of a page.

All the changes across all pages make up for the _history of the wiki_.


## Page History

You can generally see the history of a page by clicking the "_History_" entry in
the sidebar. The history will be a list of revisions, where each revision is
shown as:

- An _identifier_ for the revision, which is how the source control management
  system (SCM) knows about this revision. It depends on the SCM you chose when
  creating your wiki -- with Mercurial it's going to be a revision hash, and
  with Git it's going to be a commit SHA.

- The date when the revision occured.

- The author of the change. If the person who created or edited the page wasn't
  logged in, the IP address will be stored instead.

- A comment that the author may or may not have written when they created or
  edited the page.

- The ability to show the changes that the revision did to the page (_i.e._ the
  difference between the page's prevision revision and the selected one), and
  the ability to show the changes between two arbitrary revisions (_i.e._
  selecting two revision and showing the difference between them).


### Reverting to a Previous Revision

The revision identifier will usually be a clickable link in a page's history,
which shows you what the page's _raw text_ looked like at that point in time.

There is also a button at the bottom of that page which lets you _revert_ the
page to that revision. This will create a _new revision_ which effectively
brings that page's text back to how it was.


## Wiki History

You can look at the entire wiki's history in the special [[special:/History]]
page.

That page will show you a similar list of revisions as with page histories, but
with a different layout, because each revision will now also list the pages that
were modified in each revision. Although someone editing pages through Wikked's
web interface will only be able to change one page at a time, what sets Wikked
apart from some other wikis is that pages are simple text files stored in
a standard SCM like Git or Mercurial, so it's possible for some changes to have
been done _outside_ of Wikked (using your text editor of choice), across several
files at the same time. See [[Editing Pages]].


