#!groovy

def imageName = ''

load 'jenkins/podTemplate.groovy'


node('openshift-pod') {

    stage('Checkout') {
        checkout scm
    }

    stage('Build') {
        // pass
    }

    stage('Test') {
        // pass
    }

    stage('Push') {
        // pass
    }

    if (env.BRANCH_NAME == 'master') {
        stage('Open Pull Requests') {
            // pass
        }
    } else {
        stage('Add GitHub Comment') {
            // pass
        }
    }
}
