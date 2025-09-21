#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { BackendStack } from '../lib/backend-stack';
import { FrontendStack } from '../lib/frontend-stack';

const app = new cdk.App();

const env = {
  region: "us-east-1",
  account: "319237335445"
};

// Deploy backend stack
const backendStack = new BackendStack(app, 'BackendStack', {
  env: env
});

// Deploy frontend stack
const frontendStack = new FrontendStack(app, 'FrontendStack', {
  env: env
});

// Add dependency - frontend should be deployed after backend if needed
// frontendStack.addDependency(backendStack);