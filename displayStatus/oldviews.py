import SoftLayer, configparser,logging
from django.shortcuts import render
from displayStatus.forms import UserForm, UserProfileForm
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta

def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds / 60), 1)
    return totalminutes

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:19]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S")
    return formatedDate

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode'] == categoryCode:
            return item['description']
    return "Not Found"

def initializeSoftLayerAPI():
    filename = "config.ini"
    config = configparser.ConfigParser()
    config.read(filename)
    client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    return client

def getVirtualGuestsBeingProvisioned():
    client = initializeSoftLayerAPI()
    virtualGuests = client['Account'].getHourlyVirtualGuests(
        mask='id, provisionDate, hostname, lastTransaction, activeTransaction, activeTransactions,datacenter, datacenter.name,serverRoom, primaryBackendIpAddress, networkVlans, backendRouters,blockDeviceTemplateGroup',
        filter={
            'hourlyVirtualGuests': {
                'provisionDate': {'operation': 'is null'}
            }
    })
    return virtualGuests

def getInvoiceLists(startdate,enddate):
    client = initializeSoftLayerAPI()
    invoiceList = client['Account'].getInvoices(mask='createDate,typeCode, id', filter={
        'invoices': {
            'createDate': {
                'operation': 'betweenDate',
                'options': [
                     {'name': 'startDate', 'value': [startdate]},
                     {'name': 'endDate', 'value': [enddate]}
                     ],
                },
            'typeCode': {
                'operation': 'in',
                'options': [
                    {'name': 'data', 'value': ['ONE-TIME-CHARGE', 'NEW']}
                ]
                },
            }
        })
    return invoiceList

def vsidetail(guestId):


def getStatus(virtualGuests):
    rows=[]
    for virtualGuest in virtualGuests:
        guestId = virtualGuest['activeTransaction']['guestId']
        createDate = virtualGuest['activeTransaction']['createDate']
        createDateStamp = convert_timestamp(createDate)
        currentDateStamp = datetime.now()
        delta = convert_timedelta(currentDateStamp - createDateStamp)
        hostName = virtualGuest['hostname']
        transactionStatus = virtualGuest['activeTransaction']['transactionStatus']['name']
        statusDuration = round(virtualGuest['activeTransaction']['elapsedSeconds']/60,1)

        if 'blockDeviceTemplateGroup' in virtualGuest:
            blockDeviceTemplateGroup=virtualGuest['blockDeviceTemplateGroup']['name']
        else:
            blockDeviceTemplateGroup="no"

        if "networkVlans" in virtualGuest:
            vlan=virtualGuest['networkVlans'][0]['vlanNumber']
        else:
            vlan=""

        if "backendRouters" in virtualGuest:
            backendRouter=virtualGuest['backendRouters'][0]['hostname']
        else:
            backendRouter=""

        if "datacenter" in virtualGuest:
            datacenter=virtualGuest['datacenter']['name']
        else:
            datacenter=""

        if "serverRoom" in virtualGuest:
            serverRoom=virtualGuest['serverRoom']['longName']
        else:
            serverRoom=""

        if "primaryBackendIpAddress" in virtualGuest:
            primaryBackendIpAddress=virtualGuest['primaryBackendIpAddress']
        else:
            primaryBackendIpAddress=""


        if 'averageDuration' in virtualGuest['activeTransaction']['transactionStatus']:
            averageDuration=virtualGuest['activeTransaction']['transactionStatus']['averageDuration']
        else:
            averageDuration=1

        createDate=datetime.strftime(createDateStamp,"%Y-%m-%d")
        createTime=datetime.strftime(createDateStamp,"%H:%M:%S")

        status = "unknown"

        logging.info('%s using %s image behind %s on vlan %s is %s. (delta=%s, average=%s, duration=%s, request=%s).' % (guestId,blockDeviceTemplateGroup,backendRouter, vlan, status,delta,averageDuration,statusDuration,datetime.strftime(createDateStamp, "%H:%M:%S%z")))

        # IF DURATION PROGRESSING < 45 THEN ON TRACK
        if (delta) < 45:
            status = "ONTRACK"
        # IF DURATION BETWEEN 45 & 75 & PROGRESSING < 45 THEN ON AT RISK
        if (delta >= 45) and (delta < 75):
            status = "ATRISK"
        # IF DURATION > 75 & PROGRESSING THEN ON TRACK MARK AS CRITICAL ONLY
        if (delta) >= 75 and (statusDuration < 15):
            status = "CRITICAL"
        # IF DURATION > 75 & NOT PROGRESSING THEN MARK STALLED.
        if (delta) >= 60 and (statusDuration >= 15):
            status = "STALLED"

        row = {'guestId': guestId,
            'hostName': hostName,
            'blockDeviceTemplateGroup': blockDeviceTemplateGroup,
            'datacenter': datacenter,
            'serverRoom': serverRoom,
            'backendRouter': backendRouter,
            'vlan': vlan,
            'primaryBackendIpAddress': primaryBackendIpAddress,
            'createDate': createDate,
            'createTime': createTime,
            'delta': delta,
            'transactionStatus': transactionStatus,
            'averageDuration': averageDuration,
            'statusDuration': statusDuration,
            'status': status
            }
        rows.append(row)
    return rows

def getInvoicesItemStatus(invoiceList):
    rows=[]
    for invoice in invoiceList:
        invoiceID = invoice['id']
        invoiceDetail=getInvoiceDetail(invoiceID)
        invoiceTopLevelItems=invoiceDetail['invoiceTopLevelItems']
        for item in invoiceTopLevelItems:
            if item['categoryCode']=="guest_core":
                itemId = item['id']
                billingItemId = item['billingItemId']
                location=item['location']['name']
                hostName = item['hostName']
                createDateStamp = convert_timestamp(item['createDate'])
                product=item['description']
                cores=""
                billingDetail=getBillingDetail(itemId)
                os=getDescription("os", billingDetail)
                memory=getDescription("ram", billingDetail)
                disk=getDescription("guest_disk0", billingDetail)
                if 'product' in item:
                    product=item['product']['description']
                    cores=item['product']['totalPhysicalCoreCount']

                billingInvoiceItem=getBillingInvoiceItem(itemId)
                if 'provisionTransaction' in billingInvoiceItem:
                    provisionTransaction = billingInvoiceItem['provisionTransaction']
                    provisionId = provisionTransaction['id']
                    guestId = provisionTransaction['guestId']
                    provisionDateStamp = convert_timestamp(provisionTransaction['modifyDate'])
                else:
                    provisionTransaction = "0"
                    provisionId = "0"
                    guestId = "0"
                    provisionDateStamp = convert_timestamp(item['createDate'])

                powerOnDelta, powerOnDateStamp=checkForPowerOnEvent(guestId,createDateStamp)
                createDate=datetime.strftime(createDateStamp,"%Y-%m-%d")
                createTime=datetime.strftime(createDateStamp,"%H:%M:%S")
                powerOnDate=datetime.strftime(powerOnDateStamp,"%Y-%m-%d")
                powerOnTime=datetime.strftime(powerOnDateStamp,"%H:%M:%S")
                provisionDate=datetime.strftime(provisionDateStamp,"%Y-%m-%d")
                provisionTime=datetime.strftime(provisionDateStamp,"%H:%M:%S")
                provisionDelta=convert_timedelta(provisionDateStamp-createDateStamp)

                row = {'invoiceId': invoiceID,
                       'billingItemId': billingItemId,
                       'guestId': guestId,
                       'location': location,
                       'product': product,
                       'cores': cores,
                       'os': os,
                       'memory': memory,
                       'disk': disk,
                       'hostName': hostName,
                       'createDate': createDate,
                       'createTime': createTime,
                       'powerOnDate': powerOnDate,
                       'powerOnTime': powerOnTime,
                       'powerOnDelta': powerOnDelta,
                       'provisionDate': provisionDate,
                       'provisionTime': provisionTime,
                       'provisionDelta': provisionDelta
                       }
                rows.append(row)
    return rows

def getInvoiceDetail(invoiceID):
    client = initializeSoftLayerAPI()
    invoiceDetail=""
    while invoiceDetail is "":
        try:
            invoiceDetail = client['Billing_Invoice'].getObject(id=invoiceID, mask="closedDate, invoiceTopLevelItems, invoiceTopLevelItems.product,invoiceTopLevelItems.location")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Error: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)
    return invoiceDetail

def getBillingDetail(itemId):
    client = initializeSoftLayerAPI()
    billingDetail=""
    while billingDetail is "":
        try:
            billingDetail = client['Billing_Invoice_Item'].getFilteredAssociatedChildren(id=itemId)
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Error: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)
    return billingDetail

def getBillingInvoiceItem(itemId):
    client = initializeSoftLayerAPI()
    billingInvoiceItem=""
    while billingInvoiceItem is "":
        try:
           billingInvoiceItem = client['Billing_Invoice_Item'].getBillingItem(id=itemId, mask="provisionTransaction")
        except SoftLayer.SoftLayerAPIError as e:
           logging.warning("Error: %s, %s" % (e.faultCode, e.faultString))
           time.sleep(5)
    return billingInvoiceItem

def index(request):
    logging.basicConfig(filename='events.log', format='%(asctime)s %(message)s', level=logging.WARNING)
    virtualGuests = getVirtualGuestsBeingProvisioned()
    status = getStatus(virtualGuests)
    context_dict = {
        'current': datetime.strftime(datetime.now(), "%B %d, %Y %H:%M %p"),
        'status': status
        }
    response = render(request,'provisionStatus/index.html', context_dict)
    return response

def yesterday(request):
    logging.basicConfig(filename='events.log', format='%(asctime)s %(message)s', level=logging.INFO)
    yesterday = datetime.now() - timedelta(days=1)
    startdate = datetime.strftime(yesterday, "%m/%d/%Y") + " 0:0:0"
    enddate = datetime.strftime(yesterday,"%m/%d/%Y") + " 23:59:59"
    invoiceList = getInvoiceLists(startdate, enddate)
    status = getInvoicesItemStatus(invoiceList)
    context_dict = {
        'date': datetime.strftime(yesterday, "%B %d, %Y"),
        'status': status}
    response = render(request,'provisionStatus/yesterday.html', context_dict)
    return response

def register(request):

    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            # Update our variable to tell the template registration was successful.
            registered = True

        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print (user_form.errors), profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Render the template depending on the context.
    return render(request,
            'displayStatus/register.html',
            {'user_form': user_form, 'profile_form': profile_form, 'registered': registered} )

def user_login(request):

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
                # We use request.POST.get('<variable>') as opposed to request.POST['<variable>'],
                # because the request.POST.get('<variable>') returns None, if the value does not exist,
                # while the request.POST['<variable>'] will raise key error exception
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print ("Invalid login details: {0}, {1}".format(username, password))
            return HttpResponse("Invalid login details supplied.")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render(request, 'accounts/login.html', {})


@login_required
def restricted(request):
    return HttpResponse("Since you're logged in, you can see this text!")

# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/displayStatus/')