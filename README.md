# Sandman Doppler Integration

This is an integration designed to all you to access and control your Sandman Doppler inside Home Assistant. 

The integration uses local control to communicate with your Doppler using our local API: https://documenter.getpostman.com/view/14527424/VVQiv24k

This integration is still a work in progress and we hope to improve and add to it as we can. 

## What is a Sandman Doppler?

To use this integration you'll need a Sandman Doppler on your local network. The Sandman Doppler is a 6 USB charging smart clock with premium sound and Amazon Alexa built-in. If you don't have a Sandman Doppler you can buy one here: sandmandoppler.com 

## What can you use this integration for? 

Anything you'd like to do with the Sandman Doppler you can control and automate with your Home Assistant. Some ideas: 
1. Set the color of the screen based on the day of the week or month. This could be useful for garbage day or street cleaning day. 
2. Scott Hanselman is a customer of ours who has type-1 diabetes and wants to display his blood sugar on the small display of the Doppler. All this requires is a continuous glucose monitor (CGM) that is hooked up to the internet and home assistant to link the CGM and the Doppler together. Boom, now your blood sugar is displayed on the mini display of the Doppler for you to see your blood sugar at a glance. Scott and PAI CEO, Alex talked about this on Scott’s Podcast (https://hanselminutes.com/766/shipping-the-sandman-doppler-with-palo-alto-innovations-alex-tramiel) a while back and we are happy we can make this a reality for him.  
3. When your sprinklers turn on (using a smart irrigation system from a company like Rachio), the Doppler could say "enabling sprinklers"  and then turn the screen green or blue, when it's done it could turn back to your normal color. 
4. You could display the battery percentage of your phone or your electric car on the mini display. Better yet, if you forget to plug either of these in the screen could blink or change colors to remind you to plug in when you get into bed.
5. Home assistant can be granted access to your calendar so you could set multiple alarms before your meeting and flash the screen when it's time for your meeting. 
6. When the front door is opened, the Doppler could say "door" on the front screen, and if you have person detection enabled it could speak who is home.
7. When you press the 1 button it could lock all of the doors, enable your security system, turn off all the lights, set an alarm for 8 hours from now, and play white noise. You can do this with Alexa routines, but Home Assistant has more options and it would all be done locally so this would work if there was no internet access. 
8. You could program your smart smoke alarm to trigger a sound on your Doppler in case of an emergency. 
9. Have the color of the time change when it's time for bed.
10. Have the Doppler screen go to blackout mode automatically once a motion sensor stops detecting motion in your room for an hour. 

## Installation

To install this integration into your Home Assistant we are recommending your use the Home Assistant Community Store or HACS. 

1. Use [HACS](https://hacs.xyz/docs/setup/download), in `HACS > Integrations > Explore & Add Repositories` search for "Sandman Doppler". After adding this `https://github.com/pa-innovation/ha-doppler/` as a custom repository. Skip to 7.
2. If no HACS, use the tool of choice to open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
3. If you do not have a `custom_components` directory (folder) there, you need to create it.
4. In the `custom_components` directory (folder) create a new folder called `sandman_doppler`.
5. Download _all_ the files from the `custom_components/sandman_doppler/` directory (folder) in this repository.
6. Place the files you downloaded in the new directory (folder) you created.
7. Restart Home Assistant.
8. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Sandman Doppler".

<!---->

## Usage

This Sandman Doppler integration provides the following: 

These are polled every 60 seconds locally

Entities
Read/Write enties: 
-Turn the Doppler System alarm on and off


-Adjust colors of your Dopplers buttons and display in both day and night mode


-Volume Level of your Doppler


-Ascending alarms toggle on and off


-Alexa tap to talk tone 


-Alexa wake word tone toggle


-Colon blink toggle


-Colon toggle


-Day to night threshold


-Night to day threshold


-Display seconds mode (show the current time down to the second on the mini display)


-Fade time mode toggle (fade between each minute on the main display)


-Sound presets


-Volume dependent EQ toggle


-Three color and brightness syncs toggle


-12/24 time mode toggle


-Time offset


-Timezone


-Use leading zero in 24 hour mode


-Weather settings (currently you can only add location via service or the app)

Read only:
-Day or night mode indicator


-Reading of the light sensor on top of the Doppler


-Status of Alexa (logged in or not)


-How long the Doppler has been connector to Wifi


-Current Wifi SSD


-Current Wifi Signal strength

## Creating automations from smart buttons (1 or 2 on the top of the clock)

When you integrate your Doppler(s) with Home Assistant, the integration will automatically register itself with your Doppler(s) so that when a smart button is pushed, Home Assistant is notified. There are two ways to create automations for these button presses:

1. Use Device Triggers: If you are using the Automations UI to create your automation, select the Device Trigger type and then look for your Doppler device. You will see two trigger options, one for each of the smart buttons, and selecting that will automatically trigger the automation you create when the button is pressed.

2. Use Event Triggers: If you are writing your automations by hand, or if you'd prefer to use event triggers, you can trigger on the `sandman_doppler_button_pressed` event. The event data will look as follows:

```yaml
event_data:
    device_id: 12345  # The ID of the device in Home Assistant
    dsn: "Doppler-deadbeef"  # Doppler serial number. You should not have to use or remember this.
    doppler_name: "Radar"  # The name of the doppler as configured in the Sandman Clocks app
    name: "Radar"  # The name of the device in Home Assistant. If you've never changed the name of the device in Home Assistant, this will be the same as `doppler_name`
    button: 1  # Smart button number that was pressed
    action: "press"  # Push action of the smart button. Currently only `press` is supported
```

You can use this event data in triggers and conditions to decide what actions you want Home Assistant to take. To learn more about `event` triggers, refer to the [Home Assistant documentation](https://www.home-assistant.io/docs/automation/trigger/#event-trigger).

## Advanced services

Home Assistant supports the following services to use the advanced
features of Doppler from either developer tools, or more importantly
in automations. To access these go to developer tool/services and then select the service you'd like to access. Or, go to Automations in Home Assistant and select the service you'd like to autoamte. 

### Activate Lightbar Blink
This service makes the lightbar blink in one or more colors.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
If the single color selection is checked and a color is selected from
the color picker, the Doppler will blink alternating between that
color and black.

-Color List
If the color list selection is checked and a list of colors is
provided in the form [[255,0,0],[0,255,0],[0,0,255]], the the Doppler
will blink alternating between these colors.

-Rainbow
If rainbow is selected and the slider at the right is turned on, the
Doppler will alternate between the colors of the rainbow: red, orange
yellow, green, blue, purple. It is important to both check the checkbox
on the left and turn on the slider at the right if rainbow mode is
desired.  If the slider is forgotten, rainbow mode won't be selected
which may result in an error being returned by Home Asisstant.

Single Color, Color List, and Rainbow are designed to be mutually
exclusive in this service although if single color or color list is
selected in addition to Rainbow, rainbow will override all chosen
colors.

-Duration
The Duration is the length of time the effect will be on the display.
It must be selected or the service cannot be called.

-Speed
Speed adjusts how fast the Doppler alternates between the colors.  It
is optional.

-Sparkle
Sparkle turns on a cool sparkle effect when checked and low, medium,
or high is selcted.

### Activate Lightbar Comet

This service makes a comet appear on the lightbar of the Doppler.  It
can make comets of any color or rainbow comets.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
If single color is selected then a comet of a single color will streak across the screen.

-Color List
If color list is selected then comets will streak across the screen:
one in each of the colors specified in the color list.  The color list
is in the form [[255,0,0],[0,255,0],[0,0,255]]

-Rainbow
If rainbow is enabled then the comet will be rainbow colored.  It is
important to both check the checkbox on the right and turn on the
slider at the left.  If the slider is forgotten, rainbow mode won't be
selected which may result in an error being returned by Home
Asisstant.

Single Color, Color List, and Rainbow are designed to be mutually
exclusive in this service but if single color or color list is
selected when rainbow is enabled, rainbow takes precedence.

-Duration
The Duration specifies how long the effect lasts and must be selected
for the service to be called.

-Speed
Speed adjusts how fast the comet streaks across the lightbar.

-Sparkle
Sparkle turns on a cool sparkle effect when the box is checked at the
left and low, medium, or high is selected.

-Size
Size adjusts how many pixels long the comet is.

-Direction
Direction adjusts whether the comet goes from left to right (right),
right to left (left), or both directions (bounce).


### Activate Lightbar Pulse

This service makes the chosen colors slowly pulse on the lightbar
fading in from black and out to black.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
If single color is selected then this color will pulse on the light bar.

-Color List
If multiple colors in is selected and the colors are provided in the
form [[255,0,0],[0,255,0],[0,0,255]] then the lightbar will pulse each of
the provided colors and if the duration is long enough, it will repeat
the colors on the list from the beginning.

-Rainbow
If Rainbow is selected, the the lightbar will pulse each of the colors
in the rainbow: red, orange, yellow, green, blue purple.

Single Color, Color List and Rainbow are designed to be mutually
exclusive however if Single Color or Color List is provided and
rainbow is also turned on, rainbow will override the provided colors.

-Duration
Duration is the time the effect will show on the screen and must be
provided in order to call the service.

-Speed
Speed changes how fast the Doppler cycles through the colors is is pulsing.

-Sparkle
Sparkle activates a sparkle effect on the lightbar concurrently with the pulsing lights.

-Gap
Gap changes the number of frames between colors.


### Activate Lightbar Set

This service sets the lightbar to one or more colors in sequence with
no pulsing or blinking.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
Select Single Color to display one color on the lightbar.

-Color List
Multiple colors can be displayed in succession if entered in the form
[[255,0,0],[0,255,0],[0,0,255]]

-Rainbow
If the rainbow checkbox is selected on the left and the slider on the
right is also activated then the clock will set the lightbar to red,
orange, yellow, green, blue purple in sequence.

Single Color, Color List, and Rainbow are designed to be mutually
exclusive however if a Color or Color List is selected along with
Rainbow, rainbow will take precedence.

-Duration
The duration is the time that the effect shows on the clock and is required to call the service.

-Speed
The speed adjusts how long a single color is displayed.  It will make
the colors cycle more slowly if set higher.

-Sparkle
Sparkle turns on a sparkle effect.  The box on the left must be
checked and low medium or high selected for sparkle to work.


### Activate Lightbar Set-Each

This service allows the user to set the color of each individual dot
on the lightbar.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
If the Single Color Option is selected, the entire lightbar will be
turned the chosen color.

-Color List
If a color List is specified in the form
[[255,0,0],[0,255,0],[0,0,255]] then each consecutive dot on the light
bar going from left to right will be changed to the corresponding
color in the list.  If the list is less than 29 items long then the
last color on the list will be used for all dots to the right of the
listed colors on the lightbar.

-Rainbow
Ir rainbow is specified then the 29 dots will be lighted as a rainbow.

-Duration
Duration is the amount of time the effect shows on the lightbar. It
must be selected in order for the service to be called.

-Sparkle
Sparkle makes a changing sparkle effect occur in conjunction with the
dot pattern.

### Activate Lightbar Sweep
This service makes colors sweep across the lightbar.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Single Color
If single color is enabled then blocks of that color will sweep across the screen.

-Color List
If color list is enabled and colors are specified in the from
[[255,0,0],[0,255,0],[0,0,255]] then the colors will sweep across the
screen in the order of the list of colors.

-Rainbow
If Rainbow is chosen then colors will sweep across the screen in the order of the rainbow.

-Duration
Duration is the time that the effect is displayed on the screen. It is
required for the service to be called.

-Speed
Speed adjusts the amount of time it takes for the colors to proceed
across the screen.  Bigger numbers are slower.

-Sparkle
Sparkle enables a sparkling effect concurrently with the sweeping colors.

-Gap
Gap adjusts the number of black spaces between colors.

-Size
Size adjusts the width of the color blocks.

-Direction
Direction adjusts whether the effect goes from left to right (left),
right to left (right), or whether it bounces between the two
directions (Currently bounce does not work).

-Notes
A neat effect comes from activating rainbow with gap 0 and size 1.
This creates a rainbow sweeping across the lightbar.

If you want your mind blown however, do the following: Check the box
for single color and type #012107 into the color picker's custom box.
Activate rainbow mode by checking the checkbox and sliding the slider
to the right.  Check Gap and set Gap to 0 using the
selector. Likewise, check size and set Size =1 using the selector.
Pick a duration for the effect, 10 seconds is a good start.  Hit run
service and watch!


### Add New Alarm
This service sets a new alarm on the Doppler.

-Targets
Because alarms are numbered on a per clock basis, it is advisable to
select only one device when adding an alarm.

-Alarm ID
The first parameter is the Alarm ID which has to be greater than 0.

-Alarm Name
The second Parameter is Alarm Name.  This names the alarm on the Doppler.

-Alarm Time
The Alarm Time is when you would like the alarm to go off.

-Repeat Days
Check the box for Repeat Days if you would like the alarm to repeat on selected days.  The picker will allow you to select 1 or more days for the alarm to repeat.

-Alarm Color
The Alarm Color sets the color of the alarm bell on the screen of the
clock as well as the color of the alarm button when the alarm is going
off.

-Alarm Volume
The alarm volume is how loud you would like the alarm to be when it goes off.

-Alarm Enabled
If you want the alarm to go off be sure to slide the Alarm Enabled slider to the right.

-Alarm Sound
Finally, you must pick an alarm sound to be played from the list of available alarm sounds.

Delete Alarm:

Deletes an alarm on the Doppler.

-Targets
Because alarms are numbered on a per clock basis, it is advisable to select only one device when deleting an alarm.

-Alarm ID
Provide the Alarm ID to be deleted.

### Set Main Display Text

Creates a scrolling text message on the Doppler (Minus a few characters Doppler can't display.)

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more Dopplers.

-Text
Type the Text to be Displayed in the Text Field. "k","w", and "m" can't be displayed. 

-Duration
The Duration field selects how long the message will display.

-Speed
The speed field determines how fast the message scrolls across the
screen if it is too long for the Doppler.  Larger speed values make
the text scroll faster.

-Color
The Color fields allows selection of the color with which the text is displayed.

### Set Mini Display Number

This service displays a number on the mini-display where temperature
would normally be displayed.

-Targets
First, targets should be selected.  This can be a set of areas,
devices, or entities associated with one or more dopplers.

-Number
Number is the number to display on the Doppler's mini display.

-Duration
Duration is the number of seconds to to display the number.

-Color
Display color in which the number will be displayed.


### Set Weather Location

-Targets
First pick a device.  It is recommended to set the weather location on
only one device at a time.

-Location
Location is the zipcode for Dopplers in the United States.  In non US
countries, the postal code will often work if followed by a space and
the country name.  If the postal code doesn't work try the city name
followed by the country name.

## Things we would like to change/add


