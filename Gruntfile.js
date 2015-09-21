
module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    less: {
      development: {
        options: {
          paths: ["wikked/assets"]
        },
        files: {
          "wikked/static/css/wikked.min.css": "wikked/assets/css/wikked.less"
        }
      },
      production: {
        options: {
          paths: ["wikked/assets"],
          compress: true
        },
        files: {
          "wikked/static/css/wikked.min.css": "wikked/assets/css/wikked.less"
        }
      }
    },
    requirejs: {
      development: {
        options: {
          optimize: "none",
          baseUrl: "wikked/assets/js",
          mainConfigFile: "wikked/assets/js/wikked.js",
          dir: "wikked/static/js",
          modules: [
          {
              name: "wikked.app",
              include: ["require.js"]
          },
          {
              name: "wikked.edit",
              exclude: ["wikked.app"]
          }
          ]
        }
      },
      production: {
        options: {
          optimize: "uglify",
          baseUrl: "wikked/assets/js",
          mainConfigFile: "wikked/assets/js/wikked.js",
          dir: "wikked/static/js",
          modules: [
          {
              name: "wikked.app",
              include: ["require.js"]
          },
          {
              name: "wikked.edit",
              exclude: ["wikked.app"]
          }
          ]
        }
      }
    },
    imagemin: {
      all: {
        files: [{
              expand: true,
              cwd: 'wikked/assets/',
              dest: 'wikked/static/',
              src: ['img/*.{png,jpg,gif}']
        }]
      }
    },
    copy: {
      development: {
        files: [
          //{expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['img/**']},
          {expand: true, cwd: 'wikked/assets/font-awesome', dest: 'wikked/static/', src: ['fonts/**']}
        ]
      },
      dev_scripts: {
        files: [
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/wikked.js', 'js/wikked/**']}
        ]
      },
      production: {
        files: [
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/require.js']},
          {expand: true, cwd: 'wikked/assets/font-awesome', dest: 'wikked/static/', src: ['fonts/**']}
        ]
      }
    },
    jshint: {
      all: ['wikked/assets/js/wikked.js', 'wikked/assets/js/wikked/**/*.js'],
      gruntfile: ['Gruntfile.js']
    },
    watch: {
      scripts: {
        files: ['wikked/assets/js/wikked.js', 'wikked/assets/js/wikked/**'],
        tasks: ['jshint:all', 'copy:dev_scripts']
      },
      styles: {
        files: ['wikked/assets/css/**/*.less'],
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
  grunt.registerTask('dev', ['less:development', 'requirejs:development', 'copy:production', 'copy:development']);
};

