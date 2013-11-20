module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    less: {
      development: {
        options: {
          paths: ["static"]
        },
        files: {
          "build/css/wikked.min.css": "static/css/wikked.less"
        }
      },
      production: {
        options: {
          paths: ["static"],
          compress: true
        },
        files: {
          "build/css/wikked.min.css": "static/css/wikked.less"
        }
      }
    },
    requirejs: {
      development: {
        options: {
          optimize: "none",
          baseUrl: "static",
          mainConfigFile: "static/js/wikked.js",
          name: "js/wikked",
          out: "build/js/wikked.min.js"
        }
      },
      production: {
        options: {
          optimize: "uglify",
          baseUrl: "static",
          mainConfigFile: "static/js/wikked.js",
          name: "js/wikked",
          out: "build/js/wikked.min.js"
        }
      }
    },
    imagemin: {
      all: {
        files: [
          {expand: true, cwd: 'static/', dest: 'build/', src: ['img/*.{png,jpg,gif}']}
        ]
      }
    },
    copy: {
      development: {
        files: [
          {expand: true, cwd: 'static/', dest: 'build/', src: ['img/**']},
          {expand: true, cwd: 'static/', dest: 'build/', src: ['js/**']},
          {expand: true, cwd: 'static/', dest: 'build/', src: ['tpl/**']},
          {expand: true, cwd: 'static/', dest: 'build/', src: ['bootstrap/js/*.js']}
        ]
      },
      production: {
        files: [
          {expand: true, cwd: 'static/', dest: 'build/', src: ['js/require.js']},
          {expand: true, cwd: 'static/', dest: 'build/', src: ['css/*.css']},
          {expand: true, cwd: 'static/', dest: 'build/', src: ['font-awesome/font/**']}
        ]
      }
    },
    jshint: {
      all: ['static/js/wikked.js', 'static/js/wikked/**/*.js'],
      gruntfile: ['Gruntfile.js']
    },
    watch: {
      scripts: {
        files: ['static/js/**/*.js', 'static/tpl/**/*.html'],
        tasks: ['jshint', 'copy:development']
      },
      styles: {
        files: ['static/css/**/*.less'],
        tasks: ['less:development']
      },
      gruntfile: {
        files: ['Gruntfile.js'],
        tasks: ['jshint:gruntfile']
      }
    }
  });

  // Load plugins.
  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-requirejs');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-contrib-jshint');
  grunt.loadNpmTasks('grunt-contrib-watch');

  // Default task(s).
  grunt.registerTask('default', ['jshint', 'less:production', 'requirejs:production', 'imagemin:all', 'copy:production']);

  // Other tasks.
  grunt.registerTask('dev', ['less:development', 'copy:production', 'copy:development']);
};
