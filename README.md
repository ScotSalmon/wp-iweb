# wp-iweb
This is a script to import an iWeb blog to a WordPress.com site. It understands titles, inline and featured images, and the body text.

The script uses the WordPress API to actually post your iWeb content directly to WordPress; it does not generate a WordPress import/export XML file. This is mostly so that the images are imported as well, because manually uploading the media separately gets pretty messy when you have duplicate filenames (how many "IMG_0027.jpg" are there in the world?). It does mean you either have to trust the script with write permission to your WordPress blog, or be able to read Python enough to convince yourself it's safe.

To run:
1. You'll need an access token for your WordPress.com site, see https://developer.wordpress.com/docs/oauth2/. It's pretty annoying to set up just to run a script, but you can make a new dummy app that just points to any random website and then cut-n-paste the magic strings and use cURL to get your token.
2. Create your WordPress.com site. It should import fine to an existing site but I'd suggest making a new test site and importing there first, because if anything goes wrong you can end up with a ton of junk media and posts to clean out if you need to reimport. In the commands below, `<wordpress_blog>` is the "x" in x.wordpress.com.
3. You'll need the HTML output of iWeb. I don't think I could put my hands on an actual iWeb binary anymore, and this importer doesn't work on those, it works on the generated HTML.
4. (Recommended) Trial-run the script on a single post. Find a representative post in your `<iweb>/.../Entries/<year>/<month>` folders. Pick the post's base HTML file and run `iwebparseandpost.py <post_html> <auth_token> <wordpress_blog>` on it.
5. Run the script on the entire blog:
`iwebtowordpress.py <iweb_root> <auth_token> <wordpress_blog>`

Missing features:
* Clean up bulleted list import. Bulleted lists in iWeb are created with mystical incantations as part of an ancient Apple bulleted list ritual, resulting in double bullets for each list item when imported. This would be pretty easy to fix but, meh.
* Allow multiple iWeb blogs in one import command. This would be really easy but, meh.
* Read auth token from a file. Easy, meh.
* Handle WordPress URL's that aren't whatever.wordpress.com. Not exactly sure how this would work because it doesn't apply to me.
* Handle videos. Probably never going to happen, because iWeb did something awful with JavaScript for movies, and I think WordPress does something completely different that is also awful, although I don't know because I'm not paying them for a plan that has VideoPress.
