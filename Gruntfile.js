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
          baseUrl: "wikked/assets",
          mainConfigFile: "wikked/assets/js/wikked.js",
          name: "js/wikked",
          out: "wikked/static/js/wikked.min.js"
        }
      },
      production: {
        options: {
          optimize: "uglify",
          baseUrl: "wikked/assets",
          mainConfigFile: "wikked/assets/js/wikked.js",
          name: "js/wikked",
          out: "wikked/static/js/wikked.min.js"
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
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['img/**']},
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/**']},
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['tpl/**']},
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['bootstrap/js/*.js']}
        ]
      },
      dev_scripts: {
        files: [
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/wikked.js', 'js/wikked/**']}
        ]
      },
      dev_templates: {
        files: [
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['tpl/**']}
        ]
      },
      production: {
        files: [
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/require.js']},
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['js/pagedown/**']},
          {expand: true, cwd: 'wikked/assets/', dest: 'wikked/static/', src: ['font-awesome/font/**']}
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
      templates: {
        files: ['wikked/assets/tpl/**/*.html'],
        tasks: ['copy:dev_templates']
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
  grunt.registerTask('dev', ['less:development', 'copy:production', 'copy:development']);
};

