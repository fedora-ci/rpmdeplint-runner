#!groovy

def imageName = ''


pipeline {

    agent {
        node {
            label 'fedora-ci-agent'
        }
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                echo 'Build...'
            }
        }

        stage('Test') {
            steps {
                echo 'Test...'
            }
        }

        stage('Push') {
            steps {
                echo 'Push...'
            }
        }

        stage('Open Pull Requests') {
            when {
                expression { env.BRANCH_NAME == 'master' }
            }
            steps {
                echo 'Open Pull Requests...'
            }
        }

        stage('Add GitHub Comment') {
            when {
                expression { env.BRANCH_NAME != 'master' }
            }
            steps {
                echo 'Add GitHub Comment...'
            }
        }
    }
}
