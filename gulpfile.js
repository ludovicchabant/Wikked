var gulp = require('gulp');
var gulpif = require('gulp-if');
var notify = require("gulp-notify");
var argv = require('yargs').argv;

var less = require('gulp-less');
var sourcemaps = require('gulp-sourcemaps');
var cleanCSS = require('gulp-clean-css');

var imagemin   = require('gulp-imagemin');

var jshint = require('gulp-jshint');
var browserify = require('gulp-browserify');
var uglify = require('gulp-uglify');


var handleErrors = function(errorObject, callback) {
  notify.onError(errorObject
    .toString()
    .split(': ')
    .join(':\n'))
    .apply(this, arguments);
  // Keep gulp from hanging on this task
  if (typeof this.emit === 'function')
    this.emit('end');
};


gulp.task('css', function() {
  return gulp.src('wikked/assets/css/*.less')
    .pipe(gulpif(!argv.production, sourcemaps.init()))
    .pipe(less())
    .on('error', handleErrors)
    .pipe(gulpif(argv.production, cleanCSS({compatibility: 'ie8'})))
    .pipe(gulpif(!argv.production, sourcemaps.write()))
    .pipe(gulp.dest('wikked/static/css'));
});

gulp.task('fonts', function() {
  return gulp.src('node_modules/@fortawesome/fontawesome-free/webfonts/*')
    .pipe(gulp.dest('wikked/static/webfonts'));
});

gulp.task('images', function() {
  return gulp.src('wikked/assets/img/*')
    .pipe(gulpif(argv.production, imagemin()))
    .pipe(gulp.dest('wikked/static/img'));
});

gulp.task('js', function() {
  return gulp.src('wikked/assets/js/*.js')
    .pipe(jshint())
    .on('error', handleErrors)
    .pipe(browserify({
      insertGlobals : true,
      debug: !argv.production
    }))
    .on('error', handleErrors)
    .pipe(gulpif(argv.production, uglify()))
    .pipe(gulp.dest('wikked/static/js'));
});

gulp.task('default', ['css', 'fonts', 'images', 'js']);

gulp.task('watch', function() {
  gulp.watch('wikked/assets/js/**/*.js', ['js']);
  gulp.watch('wikked/assets/css/**/*.{css,less}', ['css']);
});

