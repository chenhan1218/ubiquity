import os
from collections import namedtuple
from autopilot.testcase import AutopilotTestCase
from autopilot.introspection import get_autopilot_proxy_object_for_process
from testtools.matchers import Equals, Contains
from autopilot.matchers import Eventually
from autopilot.input import Mouse, Pointer


class DefaultInstallTests(AutopilotTestCase):

    def setUp(self):
        super(DefaultInstallTests, self).setUp()
        self.app = self.launch_application()
        #properties = self.app.get_properties()
        #print(properties)
        self.pointing_device = Pointer(Mouse.create())
        
    def launch_application(self):
        '''
        Hmm... launch ubiquity


        :returns: The application proxy object.
        '''

        Pr = namedtuple('Process', ['pid'])
        my_process = Pr(int(os.environ['UBIQUITY_PID']))
        return get_autopilot_proxy_object_for_process(my_process, None)
    
    def test_default_install(self):
        '''
            Test install using all default values
        '''
        #Ubuntu: Lets get the focus back to ubiquity window
        #Comment out this line if running test on xubuntu/lubuntu and make sure terminal
        # is not on top of ubiquity when starting the test.
        #FIXME: Need setup and teardown to be implemented so we can lose this all together
        self.keyboard.press_and_release('Super+1')
        
        main_window = self.app.select_single(
            'GtkWindow', name='live_installer')
        self.assertThat(main_window.title, Equals("Install"))
        # This method runs the ubiquity_ methods to navigate testing through the install pages
        self.run_default_install_test()
        
        #Then finally here check that the complete dialog appears
        
        self.ubiquity_did_installation_complete()
    
    def ubiquity_welcome_page_test(self):
        '''
            Tests that all needed objects on the Welcome page are accessible
            
            And can also be navigated to.
            
            Once confirmed continue with install accepting all defaults
            
        '''
        self.get_welcome_page_objects()
        
        #Can we navigate to the quit button? This fails the test if object has no position attribs
        self.pointing_device.move_to_object(self.quitButton)
        
        #Can we navigate to the continue button?
        self.pointing_device.move_to_object(self.continue1_button)
        #Finally lets move on to the next page
        self.pointing_device.click()
        
    def get_welcome_page_objects(self):
        
        #Check the first page title = Welcome  
        self.headerLabel = self.app.select_single('GtkLabel', name='page_title')
        self.assertThat(self.headerLabel.label, Eventually(Contains('Welcome')))
        
        #Check that there is a 'Quit' GtkButton and the label is correct
        self.quitButton = self.app.select_single('GtkButton', name='quit')
        self.assertThat(self.quitButton.label, Equals('_Quit'))
        
        #Check that there is a continue button and has correct label
        self.continue1_button = self.app.select_single('GtkLabel', label='Continue')
        self.assertThat(self.continue1_button.label, Equals('Continue'))
    
    def ubiquity_preparing_page_test(self):
        
        self.wait_for_button_state_changed()
        #Check the next page title
        self.assertThat(self.headerLabel.label, Eventually(Contains('Preparing to install')))
        #lets get all the page objects
        
        self.get_all_preparing_page_objects()
        '''
            Lets test we can go back to the welcome page and come back here
        '''
        #Click back
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.click()
        
        self.wait_for_button_state_changed()
        #check we went back
        self.assertThat(self.headerLabel.label, Eventually(Contains('Welcome')))
        #go back to the page we were on
        self.get_welcome_page_objects()
        self.pointing_device.move_to_object(self.continue1_button)
        self.pointing_device.click()
        
        self.wait_for_button_state_changed()
        
        self.assertThat(self.headerLabel.label, Eventually(Contains('Preparing to install')))
        
        '''
            Lets navigate round all objects
        '''
        # first need to get all objects again
        self.get_all_preparing_page_objects()
        #navigate to each one
        self.pointing_device.move_to_object(self.installUpdates)
        self.pointing_device.move_to_object(self.thirdParty)
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.move_to_object(self.quitButton)
        self.pointing_device.move_to_object(self.continue_button)
        
        #Lets move on to next page now
        self.pointing_device.click()
        
    def get_all_preparing_page_objects(self):
        '''
            Lets get and check all objects
        '''
        #Check that the Quit button is still there
        self.quitButton = self.app.select_single('GtkButton', name='quit')
        self.assertThat(self.quitButton.label, Equals('_Quit'))
        #Check that the Back button is now there
        self.backButton = self.app.select_single('GtkButton', name='back')
        self.assertThat(self.backButton.label, Equals('_Back'))
        #Check the continue button is still there
        self.continue_button = self.app.select_single('GtkButton', name='next')
        self.assertThat(self.continue_button.label, Equals('Continue'))
        #also lets check both GtkCheckButtons are there for install updates & 3rd party software
        self.installUpdates = self.app.select_single('GtkCheckButton', name='prepare_download_updates')
        self.assertThat(self.installUpdates.label, Equals('Download updates while installing'))
        self.thirdParty = self.app.select_single('GtkCheckButton', name='prepare_nonfree_software')
        self.assertThat(self.thirdParty.label, Equals('Install this third-party software'))

    def ubiquity_install_type_page_test(self):

        """
            Check next page value
        """
        self.assertThat(self.headerLabel.label, Eventually(Contains('Installation type')))
        #get all page objects
        self.get_all_installtype_page_objects()  
        '''
            Test we can go back to previous page and come back here
        '''
        #Go back
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.click()

        self.wait_for_button_state_changed()

        self.assertThat(self.headerLabel.label, Eventually(Contains('Preparing to install')))
        
        #To Come back again we need to get the objects of the preparing page
        self.get_all_preparing_page_objects()
        self.pointing_device.move_to_object(self.continue_button)
        self.pointing_device.click()
        
        #check we came back ok
        self.assertThat(self.headerLabel.label, Eventually(Contains('Installation type')))
        
        '''
            Lets check we can get and navigate to all the objects
            
            If we wanted to change the install type we can just add required clicks here for
            different installation types
        '''
        #Get all the page objects again
        self.get_all_installtype_page_objects()
        
        self.pointing_device.move_to_object(self.eraseDisk)
        self.pointing_device.move_to_object(self.lvmInstall)
        self.pointing_device.move_to_object(self.somethingElseInstall)
        self.pointing_device.move_to_object(self.encryptInstall)
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.move_to_object(self.quitButton)
        self.pointing_device.move_to_object(self.continue_button)
        
        #If all is ok then lets move on to the next page
        self.pointing_device.click()
            
        
    def get_all_installtype_page_objects(self ):
        '''
            get all the installation type page objects
        '''
        self.eraseDisk = self.app.select_single('GtkRadioButton', name='use_device')
        self.assertThat(self.eraseDisk.label, Contains('Erase disk and install'))
        
        self.encryptInstall = self.app.select_single('GtkCheckButton', name='use_crypto')
        self.assertThat(self.encryptInstall.label, Equals('Encrypt the new Ubuntu installation for security'))
        
        self.lvmInstall = self.app.select_single('GtkCheckButton', name='use_lvm')
        self.assertThat(self.lvmInstall.label, Equals('Use LVM with the new Ubuntu installation'))
        
        self.somethingElseInstall = self.app.select_single('GtkRadioButton', name='custom_partitioning')
        self.assertThat(self.somethingElseInstall.label, Equals('Something else'))
        
        #Check that the Quit button is still there
        self.quitButton = self.app.select_single('GtkButton', name='quit')
        self.assertThat(self.quitButton.label, Equals('_Quit'))
        #Check that the Back button is now there
        self.backButton = self.app.select_single('GtkButton', name='back')
        self.assertThat(self.backButton.label, Equals('_Back'))
        #Check the continue button is still there
        self.continue_button = self.app.select_single('GtkButton', name='next')
        self.assertThat(self.continue_button.label, Equals('_Install Now'))

    def ubiquity_where_are_you_page_test(self):
        """
            From this point on the installation has started

            If you need to re-run the test from here then the HDD partitions need to be wiped
            and ./run_ubiquity run again

        """
        
        #check button activated
        self.wait_for_button_state_changed()

        #check we are on the correct page. 
        self.assertThat(self.headerLabel.label, Eventually(Contains('Where are you?')))
        
        #Not much to test on this page lets move on
        
        self.pointing_device.move_to_object(self.continue_button)
        
        self.pointing_device.click()
    
    
    def ubiquity_keyboard_page_test(self):
        #Check we are on the right page
        self.assertThat(self.headerLabel.label, Eventually(Contains('Keyboard layout')))
        
        #get all the page objects
        self.get_keyboard_page_objects()
        
        '''
            Test we can go back
        '''
        
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.click()
        self.wait_for_button_state_changed()
        #check we went back ok
        self.assertThat(self.headerLabel.label, Eventually(Contains('Where are you?')))
        
        #now lets go back
        
        self.continue_button = self.app.select_single('GtkButton', name='next')
        self.pointing_device.move_to_object(self.continue_button)
        self.pointing_device.click()
        #wait for button to become active again
        self.wait_for_button_state_changed()
        #check we came back ok
        self.assertThat(self.headerLabel.label, Eventually(Contains('Keyboard layout')))
        
        #We need to get the page objects again as the id's have changed
        self.get_keyboard_page_objects()
        
        '''
            Test we can test keyboard
        '''
                
        self.pointing_device.move_to_object(self.keyboardEntry)
        self.pointing_device.click()
        self.keyboard.type('This is testing that we can enter text in this GtkEntry')
        '''
            Test we can navigate round the objects
        '''
        self.pointing_device.move_to_object(self.detectKbrdLayout)
        self.pointing_device.move_to_object(self.keyboardEntry)
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.move_to_object(self.continue_button)
        #Lets move on to next page
        self.pointing_device.click()
        

        
    def get_keyboard_page_objects(self):
        '''
            Gets all the needed objects for the keyboard layout page
        '''
        # Keyboard test GtkEntry
        self.keyboardEntry = self.app.select_single('GtkEntry', name='keyboard_test')
        
        # Detect Keyboard Layout button
        self.detectKbrdLayout = self.app.select_single('GtkButton', name='deduce_layout')
        self.assertThat(self.detectKbrdLayout.label, Equals('Detect Keyboard Layout'))
        # Back Button
        self.backButton = self.app.select_single('GtkButton', name='back')
        self.assertThat(self.backButton.label, Equals('_Back'))
        # Continue Button
        self.continue_button = self.app.select_single('GtkButton', name='next')
        self.assertThat(self.continue_button.label, Contains('Continue'))
    
    def ubiquity_who_are_you_page_test(self):
        """
            This method enters the new users details on the

            'Who are you?' page
        """
        
        #assert page title
        self.assertThat(self.headerLabel.label, Eventually(Contains('Who are you')))
        
        self.get_who_are_you_page_objects()

        '''
            Test we can create a user
        '''
        
        self.keyboard.type('autopilot rocks')
        # Lets lose these tabs
        self.pointing_device.move_to_object(self.passwordEntry)
        self.pointing_device.click()

        #Intentionally cause passwords to mis-match
        self.keyboard.type('password')
        
        self.pointing_device.move_to_object(self.backButton)
        self.pointing_device.move_to_object(self.confirmPasswordEntry)
        self.pointing_device.click()

        self.keyboard.type('will_not_match')
        
        #check that passwords match, and if not redo them
        self.check_passwords_match()

        self.pointing_device.move_to_object(self.continue_button)
        self.pointing_device.click()

    def check_passwords_match(self):

        while True:

            self.continue_button = self.app.select_single('GtkButton', name='next')
            buttonSensitive = self.continue_button.sensitive

            if buttonSensitive == 1:
                self.assertThat(self.continue_button.sensitive, Equals(1))
                break

            #If passwords didn't match (which they didn't ;-) ) then retype them
            self.pointing_device.move_to_object(self.passwordEntry)
            self.pointing_device.click()
            self.keyboard.press_and_release('Ctrl+a')
            self.pointing_device.move_to_object(self.backButton)
            self.pointing_device.move_to_object(self.passwordEntry)
            self.keyboard.type('password')

            self.pointing_device.move_to_object(self.backButton)
            self.pointing_device.move_to_object(self.confirmPasswordEntry)
            self.pointing_device.click()
            self.keyboard.press_and_release('Ctrl+a')
            self.pointing_device.move_to_object(self.backButton)
            self.pointing_device.move_to_object(self.passwordEntry)
            self.keyboard.type('password')

    def get_who_are_you_page_objects(self):
        '''
            Gets all the needed objects of the Who are you? page
        '''
        #for some reason we can't select the password box with select_single directly we have to work our
        #way down the tree to get to it
        self.userGtkBox = self.app.select_single('GtkBox', name='stepUserInfo')
        self.userGtkGrid = self.userGtkBox.select_single('GtkGrid', name='userinfo_table')
        self.userHBox1 = self.userGtkGrid.select_single('GtkBox', name='hbox1')
        self.passwordEntry = self.userHBox1.select_single('GtkEntry', name='password')
        
        self.userHBox2 = self.userGtkGrid.select_single('GtkBox', name='hbox2')
        self.confirmPasswordEntry = self.userHBox2.select_single('GtkEntry', name='verified_password')
        
        self.backButton = self.app.select_single('GtkButton', name='back')
        self.assertThat(self.backButton.label, Equals('_Back'))

    def ubiquity_install_progress_bar_test(self):
        '''
            This method tracks the current progress of the install
            
            by using the fraction property of the progress bar
            
            to assertain the percentage complete.
                        
        '''
        
        #We cant assert page title here as its an external html page
        #Maybe try assert WebKitWebView is visible
        self.webkitWindow = self.app.select_single('GtkScrolledWindow', name='webkit_scrolled_window')
        self.assertThat(self.webkitWindow.visible, Eventually(Equals(1)))
        
        #Can we track the progress percentage?
        
        self.installProgress = self.app.select_single('GtkProgressBar', name='install_progress')
                
        #Copying files progress bar
        self.track_install_progress_bar()
        
        self.assertThat(self.installProgress.fraction, Eventually(Equals(0.0)))
        #And now the install progress bar
        self.track_install_progress_bar()
         
    
    def track_install_progress_bar(self):
        '''
            Gets the value of the fraction property of the progress bar
            
            so we can see when the progress bar is complete
            
        '''
        progress = 0.0
        complete = 1.0
        
        while progress < complete:

            #Lets check there have been no install errors while in this loop
            self.check_for_install_errors()
            #keep updating fraction value
            progress = self.installProgress.fraction
            # Use for debugging. Shows current 'fraction' value
            print(progress)

    def ubiquity_did_installation_complete(self):
        self.completeDialog = self.app.select_single('GtkDialog', name='finished_dialog')
        self.assertThat(self.completeDialog.title, Eventually(Contains('Installation Complete')))
        self.conTestingButton = self.completeDialog.select_single('GtkButton', name='quit_button')
        self.restartButton = self.completeDialog.select_single('GtkButton', name='reboot_button')
        self.assertThat(self.completeDialog.visible, Eventually(Equals(1)))
        
    def wait_for_button_state_changed(self):
        '''
            This waits on the continue button becoming active again, after it has been clicked
        '''
        self.continue_button = self.app.select_single('GtkButton', name='next')
        #check button disabled
        self.assertThat(self.continue_button.sensitive, Eventually(Equals(0)))
        
        objProp = self.continue_button.sensitive
        #lets wait for button to enable again
        while objProp != 1:
            #keep grabbing the button to refresh it's state
            self.continue_button = self.app.select_single('GtkButton', name='next')
            objProp = self.continue_button.sensitive

            #Check there are no errors while in this loop
            self.check_for_install_errors()
        #lets check it is enabled before returning
        self.assertThat(self.continue_button.sensitive, Eventually(Equals(1)))

    def check_for_install_errors(self):
        '''
            This checks that no error/unwanted dialogs appear

            simply asserting that their visible properties = 0

            If they are not visible then there is no problems, UI wise that is! ;-)
        '''
        # For each dialog lets, select each dialog and finally check its not visible

        crash_dialog = self.app.select_single('GtkDialog', name='crash_dialog')
        self.assertThat(crash_dialog.visible, Equals(0))

        warning_dialog = self.app.select_single('GtkDialog', name='warning_dialog')
        self.assertThat(warning_dialog.visible, Equals(0))

    def run_default_install_test(self):
        #Page 1
        self.ubiquity_welcome_page_test()
        #Page 2
        self.ubiquity_preparing_page_test()
        ##Page 3
        self.ubiquity_install_type_page_test()
        #Page 4
        self.ubiquity_where_are_you_page_test()
        #Page 5
        self.ubiquity_keyboard_page_test()
        #Page 6
        self.ubiquity_who_are_you_page_test()
        #page 7
        self.ubiquity_install_progress_bar_test()
