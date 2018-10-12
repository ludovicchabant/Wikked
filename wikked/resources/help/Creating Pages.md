
You can create new pages quite easily in Wikked using one of the following
methods:

- Using the "_New Page_" menu item in the sidebar.
- Using wiki links.
- Using the URL.

## New Page Creation

When you click on the "_New Page_" menu entry in the sidebar, you'll be taken to
an interface where you can fill in the new page's title and initial contents.
As usual with any change, there will also be an opportunity to fill in the
author's name and a description for the revision (which will show up in the
[[History]]).

If the page title contains a path separator (`/`), this will translate to
creating the page inside a sub-folder whose name is what comes before the
separator. So for example, creating a page called `Villains/Flying Monkeys` will
create a page inside a `Villains` sub-folder, with the page itself being called
`Flying Monkeys`.


## Creation via Wiki Links

An easy way to create a new page is to first reference it from another page,
_i.e._ [[Editing]] a page, and [[Linking]] to an as-of-yet inexistent page.
After saving the change, the new link should show up as red (to indicate
a missing page), and you can click that to be offered the opportunity to create
that page.

This avoids having to fill in the appropriate folder and title in the "_New
Page_" interface, and makes sure the new page is already reachable from the rest
of the wiki.


## Creation via URL

This method is a bit more nerdy, but it works as well as the previous one. You
just replace a page's title in your browser's URL bar with the title of the page
you want to create. So for example, if you're on
`https://yourwiki.net/read/Whatever` (a page titled "_Whatever_"), you can
go to `https://yourwiki.net/read/Something Else` instead. Assuming a page titled
"_Something Else_" doesn't exist already, you should get the standard "missing
page" text which will let you create it right away.


## Advanced Topics

- There's nothing preventing you from using accented or non-latin characters for
  a new page name, except for characters that would be invalid for a file name.
  However, please note that most revision control systems are going to behave
  badly if you'll be working with your repository on mixed systems (_i.e._
  Windows, Mac, Linux).

