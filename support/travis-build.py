#!/usr/bin/env python
# Build the project on Travis CI.

from __future__ import print_function
import errno, os, re, shutil, sys, tempfile, urllib
from subprocess import call, check_call, check_output, Popen, PIPE, STDOUT

def rmtree_if_exists(dir):
  try:
    shutil.rmtree(dir)
  except OSError as e:
    if e.errno == errno.ENOENT:
      pass

def makedirs_if_not_exist(dir):
  try:
    os.makedirs(dir)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

build = os.environ['BUILD']
if build == 'Doc':
  travis = 'TRAVIS' in os.environ
  # Install dependencies.
  if travis:
    branch = os.environ['TRAVIS_BRANCH']
    if branch != 'master':
      print('Branch: ' + branch)
      exit(0) # Ignore non-master branches
    check_call('curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | ' +
               'sudo apt-key add -', shell=True)
    check_call('echo "deb https://deb.nodesource.com/node_0.10 precise main" | ' +
               'sudo tee /etc/apt/sources.list.d/nodesource.list', shell=True)
    check_call(['sudo', 'apt-get', 'update'])
    check_call(['sudo', 'apt-get', 'install', 'python-virtualenv', 'nodejs'])
    check_call(['npm', 'install', '-g', 'less', 'less-plugin-clean-css'])
    deb_file = 'doxygen_1.8.6-2_amd64.deb'
    urllib.urlretrieve('http://mirrors.kernel.org/ubuntu/pool/main/d/doxygen/' +
                       deb_file, deb_file)
    check_call(['sudo', 'dpkg', '-i', deb_file])
  cppformat_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
  sys.path.insert(0, os.path.join(cppformat_dir, 'doc'))
  import build
  html_dir = build.build_docs()
  repo = 'cppformat.github.io'
  if travis and 'KEY' not in os.environ:
    # Don't update the repo if building on Travis from an account that doesn't
    # have push access.
    print('Skipping update of ' + repo)
    exit(0)
  # Clone the cppformat.github.io repo.
  rmtree_if_exists(repo)
  git_url = 'https://github.com/' if travis else 'git@github.com:'
  check_call(['git', 'clone', git_url + 'cppformat/{}.git'.format(repo)])
  # Copy docs to the repo.
  target_dir = os.path.join(repo, 'dev')
  rmtree_if_exists(target_dir)
  shutil.copytree(html_dir, target_dir, ignore=shutil.ignore_patterns('.*'))
  if travis:
    check_call(['git', 'config', '--global', 'user.name', 'amplbot'])
    check_call(['git', 'config', '--global', 'user.email', 'viz@ampl.com'])
  # Push docs to GitHub pages.
  check_call(['git', 'add', '--all'], cwd=repo)
  if call(['git', 'diff-index', '--quiet', 'HEAD'], cwd=repo):
    check_call(['git', 'commit', '-m', 'Update documentation'], cwd=repo)
    cmd = 'git push'
    if travis:
      cmd += ' https://$KEY@github.com/cppformat/cppformat.github.io.git master'
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT, cwd=repo)
    # Print the output without the key.
    print(p.communicate()[0].replace(os.environ['KEY'], '$KEY'))
    if p.returncode != 0:
      raise CalledProcessError(p.returncode, cmd)
  exit(0)

cppStandard = os.environ['STANDARD']
srcDir = os.getcwd()
srcDir_test = os.path.join(srcDir,"test","find-package-test")

installDir    = os.path.join(srcDir,"_install")
buildDir      = os.path.join(srcDir,"_build")
buildDir_test = os.path.join(srcDir,"_build_test")

# configure library
makedirs_if_not_exist(buildDir)
os.chdir(buildDir)
if cppStandard == '98':
  check_call(['cmake', '-DCMAKE_INSTALL_PREFIX='+installDir,
                       '-DCMAKE_BUILD_TYPE=' + build,
                       '-DCMAKE_CXX_FLAGS=-std=c++98',
                       '-DFMT_USE_CPP11=OFF',
                       '-DFMT_DOC=OFF',
                       '-DFMT_PEDANTIC=ON',
                       srcDir])
else:
  # default configuration
  check_call(['cmake', '-DCMAKE_INSTALL_PREFIX='+installDir,
                       '-DCMAKE_BUILD_TYPE=' + build,
                       '-DFMT_DOC=OFF',
                       '-DFMT_PEDANTIC=ON',
                       srcDir])

# build library
check_call(['make', '-j4'])

# test library
env = os.environ.copy()
env['CTEST_OUTPUT_ON_FAILURE'] = '1'
if call(['make', 'test'], env=env):
  with open('Testing/Temporary/LastTest.log', 'r') as f:
    print(f.read())
  sys.exit(-1)

# install library
check_call(['make', 'install'])

# test installation
makedirs_if_not_exist(buildDir_test)
os.chdir(buildDir_test)
if cppStandard == '98':
  check_call(['cmake', '-DCMAKE_INSTALL_PREFIX='+installDir,
                       '-DCMAKE_BUILD_TYPE=' + build,
                       '-DCMAKE_CXX_FLAGS=-std=c++98',
                       srcDir_test])
else:
  check_call(['cmake', '-DCMAKE_INSTALL_PREFIX='+installDir,
                       '-DCMAKE_BUILD_TYPE=' + build,
                       srcDir_test])
check_call(['make', '-j4'])