
WIKKED_LESS 	= ./static/css/wikked.less
WIKKED_CSS 		= ./static/css/wikked.min.css
REQUIREJS_BUILD = ./static/.rbuild.js

DATE=$(shell date +%I:%M%p)
CHECK=\033[32m✔\033[39m

build:
	@echo ""
	@echo "Building Wikked..."
	@echo ""
	@recess --compile --compress ${WIKKED_LESS} > ${WIKKED_CSS}
	@echo "Compiling LESS stylesheets...       ${CHECK} Done"
	@r.js -o ${REQUIREJS_BUILD}
	@echo "Compiling Javascript code...        ${CHECK} Done"
	@echo ""
	@echo "Successfully compiled Wikked."
	@echo ""

clean:
	rm ${WIKKED_CSS}

watch:
	recess ${WIKKED_LESS}:${WIKKED_CSS} --watch

