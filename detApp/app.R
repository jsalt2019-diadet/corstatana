#
# A. Cristia for JSALT 2019
# alecristia@gmail.Com

### TODO
# incorporate name+description using accompanying txt file

# i did the following to get the file lists
# grep "Mix" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdiar_ami_eval_Mix-Headset/plda_scores_tbest/result.pyannote-der | grep -v "arn" | cut -f 1 -d " " > ami_test.txt
# grep "jsalt" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdet_sri_eval_test/plda_scores_tbest/result.pyannote-der | grep -v "arn" | cut -f 1 -d " " > sri_test.txt
# grep "_" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdet_babytrain_eval_test/plda_scores_tbest/result.pyannote-der  | grep -v "arn" | cut -f 1 -d " " > babytrain_test.txt
# grep "_U01" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdiar_chime5_eval_U01/plda_scores_tbest/result.pyannote-der  | grep -v "arn" | cut -f 1 -d " " > chime5_test.txt



library(shiny)
library(RCurl)



# Define UI for application that draws a histogram
ui <- fluidPage(
  
  # Application title
  titlePanel("JSALT 2019 spk det leaderboard"),
  
  # Sidebar with a slider input for number of bins 
  sidebarLayout(
    sidebarPanel(
      selectInput(
        "corpus",
        "Corpus",
        c("BabyTrain" = "babytrain",
          "AMI" = "ami",
          "SRI" = "sri"
        ) 
      ),
      selectInput(
        "mic",
        "Microphone restriction",
        c("any" = "any",
          "clo" = "clo",
          "clofarwall" = "clofarwall",
          "clomed" = "clomed",
          "far" = "far",
          "med" = "med",
          "sub" = "sub",
          "tv" = "tv"
        ) 
      ),
      selectInput(
        "enr",
        "Enrolment length",
        c("any" = "any",
          "5" = "5",
          "15" = "15",
          "30" = "30"
        ) 
      ),
      selectInput(
        "test",
        "Test length",
        c("any" = "any",
          "5" = "5",
          "15" = "15",
          "30" = "30"
        ) 
      ),
      checkboxInput("adapt", "Look at adapted systems",FALSE)
    ),
    
    # Show a plot of the generated distribution
    mainPanel(
      plotOutput("rank"),
      tabPanel("Data",DT::dataTableOutput("mytable"))
    )
  )
)

# Define server logic required to draw a histogram
server <- function(input, output) {
  myurl <- getURL("https://raw.githubusercontent.com/jsalt-coml/corstatana/master/demon/allresDet.txt")
allres <- read.table(text = myurl,header=T)
#basic cleaning
allres$file=gsub("resDet/","",gsub("_clean","",allres$file))
allres[grep("eval",allres$file),]->allres
allres$corpus=gsub("_.*","",gsub(".*spkdet_","",allres$file))

#add features
  #adaptation
allres$adapt=F
allres$adapt[grep("adapt",allres$file)]=T
  #microphone
allres$mic=gsub(".*_","",allres$file)
allres$mic[grep("test",allres$mic)]<-NA
allres$mic[grep("enr",allres$mic)]<-NA
  #enrollment and test length
allres$lenenr=gsub("_.*","",gsub(".*enr","",allres$file))
allres$lent=gsub("_.*","",gsub(".*test","",allres$file))


output$rank <- renderPlot({
  # generate bins based on input$bins from ui.R
  x    <- allres[allres$corpus == input$corpus, ] 
  if(input$mic!="any") x<-x[x$mic == input$mic, ] 
  if(input$enr!="any") x<-x[x$lenenr == input$enr, ] 
  if(input$test!="any") x<-x[x$lent == input$test, ] 
  if(input$adapt) x <- x[x$adapt, ] 
  x=x[order(x$main),]
  
  
  mylabs=x$file

  # draw barplot ordering contributions by best to worst
  par(mar=c(8, 4, 2, 2.5))
  barplot(x$main, beside=T,  main=paste(input$task,"by system in",input$corpus), ylab="Equal Err R",
          xaxt="n",xlab="",ylim=c(0,100))
  end_point = 0.8 + length(x$main)*1.2 -1 #this is the line which does the trick (together with barplot "space = 1" parameter)
  text(seq(0.8,end_point,by=1.2), par("usr")[3]-0.25, 
       srt = 45, adj= 1, xpd = TRUE, 
       labels = mylabs)
})

output$mytable = DT::renderDataTable({
  x    <- allres[allres$corpus == input$corpus, ] 
  if(input$mic!="any") x<-x[x$mic == input$mic, ] 
  if(input$enr!="any") x<-x[x$lenenr == input$enr, ] 
  if(input$test!="any") x<-x[x$lent == input$test, ] 
  if(input$adapt) x <- x[x$adapt, ] 
  x=x[order(x$main),]
  
  x
  
},rownames = FALSE)
}

# Run the application 
shinyApp(ui = ui, server = server)
